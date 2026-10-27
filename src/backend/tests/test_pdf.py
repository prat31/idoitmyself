"""PDF text extraction: the simple-font /Widths guard and the error it produces."""

from io import BytesIO

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.errors import LimitReachedError
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject

from app.processors.outcomes import Fail
from app.processors.pdf import _trim_oversized_widths, pdf_text


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def pdf_with_widths(count: int) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=100, height=100)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Calibri"),
            NameObject("/FirstChar"): NumberObject(1),
            NameObject("/Widths"): ArrayObject([NumberObject(500)] * count),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def test_oversized_widths_are_trimmed():
    reader = PdfReader(BytesIO(pdf_with_widths(257)))
    assert _trim_oversized_widths(reader) is True
    fonts = reader.pages[0]["/Resources"].get_object()["/Font"].get_object()
    assert len(fonts["/F1"].get_object()["/Widths"].get_object()) == 256
    assert _trim_oversized_widths(reader) is False


def test_limit_reached_is_retried_after_trimming(monkeypatch):
    calls = []

    def extract_text(self, *args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise LimitReachedError("Too many character widths: 257 > 256.")
        return "statement text"

    monkeypatch.setattr("pypdf._page.PageObject.extract_text", extract_text)
    assert pdf_text(pdf_with_widths(257), None) == "statement text"
    assert len(calls) == 2


def test_an_unfixable_limit_reached_is_reported(monkeypatch):
    def extract_text(self, *args, **kwargs):
        raise LimitReachedError("CID width range too large: 999999 > 65536.")

    monkeypatch.setattr("pypdf._page.PageObject.extract_text", extract_text)
    with pytest.raises(Fail, match="CID width range too large"):
        pdf_text(blank_pdf(), None)


def test_other_extraction_errors_are_reported(monkeypatch):
    def extract_text(self, *args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr("pypdf._page.PageObject.extract_text", extract_text)
    with pytest.raises(Fail, match="ValueError: boom"):
        pdf_text(blank_pdf(), None)


def test_a_pdf_with_no_text_still_says_it_may_be_scanned():
    with pytest.raises(Fail, match="scanned image"):
        pdf_text(blank_pdf(), None)
