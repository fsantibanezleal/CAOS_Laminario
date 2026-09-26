"""The z-plane policy: which planes of a focal stack are kept.

A stack's full pyramid set is estimated from its plane count and the measured size of one plane's pyramid.
When the estimate fits the budget the whole stack is kept. Otherwise ``KEPT_PLANES`` planes are chosen,
evenly spaced and always including both ends, and each kept plane records its original index and depth so
the viewer labels real focal depths.
"""

from __future__ import annotations

from dataclasses import dataclass

STACK_BUDGET_BYTES = 500 * 1_000_000
KEPT_PLANES = 11


@dataclass(frozen=True)
class Plane:
    index: int
    depth_um: float


@dataclass(frozen=True)
class Selection:
    kept: tuple[Plane, ...]
    total: int
    resampled: bool
    estimated_bytes: int


def resample_indices(n: int, k: int = KEPT_PLANES) -> list[int]:
    """``k`` indices out of ``n``, evenly spaced, both ends included, strictly increasing when n >= k."""
    if n <= k:
        return list(range(n))
    return [round(i * (n - 1) / (k - 1)) for i in range(k)]


def select_planes(planes: list[Plane], bytes_per_plane_pyramid: int) -> Selection:
    """Apply the policy to a stack whose planes are given in acquisition order."""
    ordered = sorted(planes, key=lambda p: p.index)
    estimate = len(ordered) * bytes_per_plane_pyramid
    if estimate <= STACK_BUDGET_BYTES:
        return Selection(tuple(ordered), len(ordered), False, estimate)
    kept = tuple(ordered[i] for i in resample_indices(len(ordered)))
    return Selection(kept, len(ordered), True, estimate)
