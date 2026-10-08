"""Privacy guardrails for the chat (Problem 9).

1. Input: card numbers, US social security numbers and "my password is …" phrases are removed from
   a shopper's message BEFORE it reaches the model, the database (chat_messages) or the audit trail.
2. Output: a reply may only contain email addresses that belong to the shopper or the store.
"""

from __future__ import annotations

import re

STORE_EMAILS = {"orderdept@campuscustoms.com", "team@campuscustoms.com"}

_CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
_SSN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_PASSWORD = re.compile(r"\b(pass(?:word|code)|pwd)\b(\s*(?:is|=|:)\s*)\S+", re.IGNORECASE)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _luhn_ok(digits: str) -> bool:
    total, double = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if double:
            d = d * 2 - 9 if d > 4 else d * 2
        total, double = total + d, not double
    return total % 10 == 0


def redact(text: str) -> tuple[str, list[str]]:
    """Return the text with sensitive numbers/secrets removed, plus what kinds were removed."""
    removed: list[str] = []

    def card(match: re.Match) -> str:
        digits = re.sub(r"\D", "", match.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            removed.append("card number")
            return "[card number removed]"
        return match.group()

    text = _CARD.sub(card, text)
    text, n = _SSN.subn("[SSN removed]", text)
    removed += ["SSN"] * n
    text, n = _PASSWORD.subn(lambda m: f"{m.group(1)}{m.group(2)}[removed]", text)
    removed += ["password"] * n
    return text, removed


def foreign_emails(reply: str, shopper_email: str | None) -> list[str]:
    """Emails in a reply that are neither the shopper's own nor the store's."""
    allowed = STORE_EMAILS | ({shopper_email.lower()} if shopper_email else set())
    return sorted({e for e in EMAIL.findall(reply) if e.lower() not in allowed})
