"""The QR of a slide: its permalink in upper case, in the alphanumeric mode, at error correction M (dossier 05,
section 3: version 3, 29 by 29 modules, for Laminario's host and an eight-character short id).

The canonical encoded form is upper case because the alphanumeric mode has no lower-case letters; the same URL in
lower case needs byte mode and version 4. Host names are case-insensitive by definition, and the server reads a short
id in any case, so the upper-case URL opens the same slide.
"""

from __future__ import annotations

from dataclasses import dataclass

import segno

#: The white margin a reader needs around the symbol, in modules (ISO/IEC 18004).
QUIET_MODULES = 4


@dataclass(frozen=True)
class Symbol:
    payload: str
    version: int
    mode: str
    #: rows of modules, True where dark, without the quiet zone
    modules: tuple[tuple[bool, ...], ...]

    @property
    def size(self) -> int:
        return len(self.modules)


def symbol(payload: str) -> Symbol:
    code = segno.make_qr(payload, error="m", mode="alphanumeric", boost_error=False)
    rows = tuple(tuple(bool(v) for v in row) for row in code.matrix)
    return Symbol(payload=payload, version=int(code.version), mode=code.mode, modules=rows)
