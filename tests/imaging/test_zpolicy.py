"""The z-plane policy: keep the whole stack within budget, otherwise 11 evenly spaced planes."""

from __future__ import annotations

from app.imaging import zstack


# R-014
def test_resample_indices_and_depths():
    for n in (12, 20, 41, 71, 81, 200):
        kept = zstack.resample_indices(n)
        assert len(kept) == zstack.KEPT_PLANES
        assert kept[0] == 0 and kept[-1] == n - 1
        assert all(b > a for a, b in zip(kept, kept[1:], strict=False))
    assert zstack.resample_indices(71) == [0, 7, 14, 21, 28, 35, 42, 49, 56, 63, 70]
    planes = [zstack.Plane(index=i, depth_um=-70.0 + 2.0 * i) for i in range(71)]
    over = zstack.select_planes(planes, bytes_per_plane_pyramid=10_000_000)  # 710 MB estimated
    assert over.resampled and over.total == 71
    assert [p.index for p in over.kept] == zstack.resample_indices(71)
    assert [p.depth_um for p in over.kept] == [-70.0 + 2.0 * i for i in zstack.resample_indices(71)]
    within = zstack.select_planes(planes, bytes_per_plane_pyramid=7_000_000)  # 497 MB estimated
    assert not within.resampled and len(within.kept) == 71


def test_small_stacks_are_kept_whole():
    assert zstack.resample_indices(5) == [0, 1, 2, 3, 4]
    shuffled = [zstack.Plane(3, 3.0), zstack.Plane(0, 0.0), zstack.Plane(1, 1.0)]
    assert [p.index for p in zstack.select_planes(shuffled, 1).kept] == [0, 1, 3]
