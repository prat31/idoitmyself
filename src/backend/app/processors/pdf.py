"""Reading text out of PDFs, locally (pypdf). Password-protected PDFs need the password the user saved
for the sender and label."""

import logging
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.errors import LimitReachedError, PdfReadError
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject, NameObject

from app.processors.outcomes import Fail

logger = logging.getLogger(__name__)

# A simple (TrueType/Type1) font only has character codes 0-255, so this many /Widths entries is the
# most pypdf reads.
_MAX_SIMPLE_FONT_WIDTHS = 256
# A safety cap on the walk that trims oversized /Widths arrays.
_MAX_OBJECTS_INSPECTED = 50_000


class PdfPasswordRequired(Exception):
    """The PDF is protected and no password was given (`wrong` False), or the given one didn't open it."""

    def __init__(self, wrong: bool):
        super().__init__(
            "The saved password didn't open the PDF" if wrong else "The PDF is password-protected"
        )
        self.wrong = wrong


def is_pdf(filename: str, mime_type: str) -> bool:
    return mime_type == "application/pdf" or filename.lower().endswith(".pdf")


def _describe(exc: Exception) -> str:
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _trim_oversized_widths(reader: PdfReader) -> bool:
    """Trim simple-font /Widths arrays to the 256 entries pypdf reads.

    pypdf 6.18.1 and later reject a TrueType/Type1 font with more /Widths entries than that, as a
    guard against memory exhaustion from hostile PDFs (GHSA-g9cg-prrw-2r8q). Real statements go one
    over (Axis's Calibri: /FirstChar 1 and 257 entries), and pypdf ignores codes above 255 anyway, so
    dropping the extras lets the statement read while the guard stays in place for everything else.
    Returns whether anything was trimmed."""
    changed = False
    seen: set[int] = set()
    pending: list[Any] = [reader.trailer["/Root"]]
    while pending and len(seen) < _MAX_OBJECTS_INSPECTED:
        obj = pending.pop()
        try:
            if isinstance(obj, IndirectObject):
                obj = obj.get_object()
            if not isinstance(obj, (DictionaryObject, ArrayObject)) or id(obj) in seen:
                continue
            seen.add(id(obj))
            if isinstance(obj, DictionaryObject):
                widths = obj.get("/Widths")
                if widths is not None:
                    widths = widths.get_object()
                    if isinstance(widths, ArrayObject) and len(widths) > _MAX_SIMPLE_FONT_WIDTHS:
                        obj[NameObject("/Widths")] = ArrayObject(widths[:_MAX_SIMPLE_FONT_WIDTHS])
                        changed = True
                pending.extend(obj.values())
            else:
                pending.extend(obj)
        except Exception as exc:  # a malformed object: leave it for pypdf to deal with
            logger.debug("PDF object not inspected: %r", exc)
    return changed


def pdf_text(data: bytes, password: str | None) -> str:
    """The PDF's text, page by page. Raises PdfPasswordRequired, or Fail for a broken PDF or one
    with no text (a scanned image: there's no OCR)."""
    try:
        reader = PdfReader(BytesIO(data))
        # Some PDFs are encrypted with an empty password (they open without asking): try that first.
        if reader.is_encrypted and not reader.decrypt(""):
            if password is None:
                raise PdfPasswordRequired(wrong=False)
            if not reader.decrypt(password):
                raise PdfPasswordRequired(wrong=True)
        pages = list(reader.pages)
    except PdfReadError as exc:
        raise Fail(f"Couldn't read the PDF: {exc}") from exc
    texts: list[str] = []
    problems: list[str] = []
    trimmed = False
    for number, page in enumerate(pages, start=1):
        while True:
            try:
                texts.append(page.extract_text() or "")
                break
            except LimitReachedError as exc:
                # pypdf's security guard, not a real failure: fix the offending font and try again.
                if not trimmed and _trim_oversized_widths(reader):
                    trimmed = True
                    continue
                logger.warning("PDF page %s: text not extracted: %r", number, exc)
                problems.append(f"page {number}: {_describe(exc)}")
                break
            except Exception as exc:  # an odd font on a page of fine print: skip the page, keep the rest
                logger.warning("PDF page %s: text not extracted: %r", number, exc)
                problems.append(f"page {number}: {_describe(exc)}")
                break
    text = "\n".join(texts)
    if not text.strip():
        if problems:
            detail = "; ".join(problems[:3]) + (" …" if len(problems) > 3 else "")
            raise Fail(f"Couldn't extract text from the PDF ({detail})")
        raise Fail("The PDF has no text (it may be a scanned image)")
    return text
