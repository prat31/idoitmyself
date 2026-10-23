import html
import re

_SCRIPT_STYLE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_BREAKS = re.compile(r"<\s*(br|/p|/div|/li|/tr|/h[1-6])\b[^>]*>", re.IGNORECASE)
_TAGS = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"[ \t\f\v ]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


def html_to_text(markup: str) -> str:
    """Rough HTML → plain text, good enough for classification."""
    text = _SCRIPT_STYLE.sub(" ", markup)
    text = _BREAKS.sub("\n", text)
    text = _TAGS.sub(" ", text)
    return normalize_whitespace(html.unescape(text))


def normalize_whitespace(text: str) -> str:
    text = _SPACES.sub(" ", text.replace("\r\n", "\n").replace("\r", "\n"))
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _BLANK_LINES.sub("\n\n", text).strip()
