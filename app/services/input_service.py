from __future__ import annotations

import re

import bleach

from app.core.exceptions import DomainError

SCRIPT_TAG_PATTERN = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)


def sanitize_input(text: str) -> str:
    cleaned = SCRIPT_TAG_PATTERN.sub("", text)
    cleaned = bleach.clean(cleaned, tags=[], strip=True)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def validate_text_length(text: str, minimum: int = 100, maximum: int = 50000) -> None:
    if len(text) < minimum:
        raise DomainError("TEXT_TOO_SHORT", f"Text length must be >= {minimum} chars", 422)
    if len(text) > maximum:
        raise DomainError("TEXT_TOO_LONG", f"Text length must be <= {maximum} chars", 422)
