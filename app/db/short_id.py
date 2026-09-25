"""Short slide ids in Crockford's base 32.

Eight characters from ``0123456789ABCDEFGHJKMNPQRSTVWXYZ`` (no I, L, O, U) give 40 bits. They are printed
upper case on labels because the uppercase permalink encodes in the QR alphanumeric mode, one QR version
smaller than the lowercase one. Reading is forgiving, as Crockford specifies: letter case is ignored, ``I``
and ``L`` read as ``1``, ``O`` reads as ``0``, and hyphens are dropped.
"""

from __future__ import annotations

import re
import secrets

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
LENGTH = 8
_VALID = re.compile(rf"^[{ALPHABET}]{{{LENGTH}}}$")


def generate() -> str:
    """A new random short id (not yet checked for uniqueness)."""
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalise(text: str) -> str | None:
    """The canonical form of a short id as typed or scanned, or ``None`` when it cannot be one."""
    cleaned = text.strip().upper().replace("-", "")
    cleaned = cleaned.translate(str.maketrans({"I": "1", "L": "1", "O": "0"}))
    return cleaned if _VALID.match(cleaned) else None
