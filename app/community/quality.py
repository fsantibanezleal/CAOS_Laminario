"""The badge (M9, R-1304): the slide checks and the community together (dossier 15, sections 3 and 5).

iNaturalist's ``get_quality_grade`` with Laminario's depths: a slide whose checks fail is *reference*; one that more
identifiers say still needs identification than say it is as good as it can be is *needs ID*; one whose community
anchor is as fine as its kind needs is *verified*; one voted as good as it can be is *verified* when its anchor is at
the coarser depth its kind allows, and *reference* when coarser still; the rest need identification.
"""

from __future__ import annotations

from typing import Literal

from app.community.lineage import depth_of

Badge = Literal["verified", "needs_id", "reference"]


def badge(checks_pass: bool, node: str | None, rank: str | None, as_good: int, needs_more: int) -> Badge:
    if not checks_pass:
        return "reference"
    if needs_more > as_good:
        return "needs_id"
    if node is None:
        return "needs_id"
    depth = depth_of(node, rank)
    if depth.enough:
        return "verified"
    if as_good > needs_more:
        return "verified" if depth.allowed_when_voted else "reference"
    return "needs_id"
