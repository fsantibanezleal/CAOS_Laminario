"""Extended depth of field against the EPFL plugin's own output and against known focus.

The plugin's outputs were produced once with its unmodified jar through ``RunEdf.java`` (kept with the
fixtures), presets "high" (complex wavelets) and "low-medium" (variance, window 5), on its three sample
stacks: a colony dome (499 x 363, 20 planes, RGB), a fly eye (680 x 500, 32 planes, 32-bit grey) and a
skeleton (170 x 116, 3 planes, RGB).
"""

from __future__ import annotations

import numpy as np
import pytest
import tifffile
from skimage.metrics import structural_similarity

from app.imaging import edf

from .synthetic import focal_stack

CASES = ["dome", "eye", "skeleton"]
SQUARE_PADDED = ["dome"]  # 499 x 363 pads to 512 x 512; the others pad to 1024 x 512 and 256 x 128


def reference(root, case, preset):
    stack = tifffile.imread(root / case / "stack.tif")
    composite = tifffile.imread(root / case / f"{preset}-composite.tif")
    height = tifffile.imread(root / case / f"{preset}-heightmap.tif").astype(np.int32)
    return stack, composite, height


def similarity(a, b):
    if a.ndim == 3:
        return structural_similarity(a, b, channel_axis=2, data_range=255)
    span = float(b.max() - b.min())
    return structural_similarity(a.astype(np.float64), b.astype(np.float64), data_range=span)


def grey(image):
    return edf.luminance(image) if image.ndim == 3 else image


# R-015
@pytest.mark.parametrize("case", CASES)
def test_variance_baseline_sharpness(edf_reference, case):
    stack, _, _ = reference(edf_reference, case, "variance")
    result = edf.fuse_array(stack, edf.METHOD_VARIANCE)
    sharpest_plane = max(edf.tenengrad(grey(plane)) for plane in stack)
    assert edf.tenengrad(grey(result.composite)) >= 0.95 * sharpest_plane


# R-016
@pytest.mark.parametrize("case", SQUARE_PADDED)
def test_wavelet_parity_with_reference(edf_reference, case):
    stack, composite, _ = reference(edf_reference, case, "high")
    wavelet = edf.fuse_array(stack, edf.METHOD_WAVELET)
    variance = edf.fuse_array(stack, edf.METHOD_VARIANCE)
    score = similarity(wavelet.composite, composite)
    assert score >= 0.90
    assert score >= similarity(variance.composite, composite)


# R-204
@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("preset", ["high", "variance"])
def test_port_exact_with_plugin_axes(edf_reference, case, preset):
    stack, composite, height = reference(edf_reference, case, preset)
    method = edf.METHOD_WAVELET if preset == "high" else edf.METHOD_VARIANCE
    result = edf.fuse_array(stack, method, plugin_axes=True)
    assert np.mean(result.height_map.astype(np.int32) == height) >= 0.999
    assert similarity(result.composite, composite) >= 0.999


# R-205
@pytest.mark.parametrize("size", [(128, 256, 12, 1), (170, 300, 16, 2), (256, 256, 16, 3)])
def test_true_geometry_beats_plugin_axes(size):
    h, w, planes, seed = size
    stack, sharp, truth = focal_stack(h, w, planes, seed)
    scores = {}
    for axes in (True, False):
        result = edf.fuse_array(stack, edf.METHOD_WAVELET, plugin_axes=axes)
        within = np.mean(np.abs(result.height_map.astype(int) - truth) <= 1)
        rmse = np.sqrt(np.mean((result.composite.astype(float) - sharp) ** 2))
        scores[axes] = (within, rmse)
    assert scores[False][0] >= scores[True][0]
    assert scores[False][1] <= scores[True][1]
    if h != w:
        assert scores[False][0] >= scores[True][0] + 0.3  # measured 0.50 to 0.51 better on these sizes


# R-206
def test_depth_readout_from_variance_is_accurate():
    for noise in (0.0, 3.0):
        stack, _, truth = focal_stack(170, 300, 16, 2, noise=noise)
        result = edf.fuse_array(stack, edf.METHOD_VARIANCE)
        assert np.mean(np.abs(result.height_map.astype(int) - truth) <= 1) >= 0.95


# R-207
def test_tiled_matches_whole():
    stack, sharp, truth = focal_stack(420, 700, 12, 7)
    variance_whole = edf.fuse_array(stack, edf.METHOD_VARIANCE, tile=4096)
    variance_tiled = edf.fuse_array(stack, edf.METHOD_VARIANCE, tile=256, margin=64)
    assert np.array_equal(variance_whole.height_map, variance_tiled.height_map)
    whole = edf.fuse_array(stack, edf.METHOD_WAVELET, tile=4096)
    tiled = edf.fuse_array(stack, edf.METHOD_WAVELET, tile=256, margin=64)

    def within(result):
        return np.mean(np.abs(result.height_map.astype(int) - truth) <= 1)

    def rmse(result):
        return np.sqrt(np.mean((result.composite.astype(float) - sharp) ** 2))

    assert within(tiled) >= within(whole) - 0.02
    assert rmse(tiled) <= 1.05 * rmse(whole)


def test_colour_composite_takes_pixels_from_the_named_plane():
    rng = np.random.default_rng(3)
    stack = rng.integers(0, 256, (5, 40, 60, 3), dtype=np.uint8)
    result = edf.fuse_array(stack, edf.METHOD_VARIANCE)
    k = result.height_map.astype(int) - 1
    rows, cols = np.mgrid[0:40, 0:60]
    assert np.array_equal(result.composite, stack[k, rows, cols])


def test_depth_map_uses_plane_depths():
    stack, _, _ = focal_stack(64, 64, 4, 9)
    result = edf.fuse_array(stack, edf.METHOD_VARIANCE)
    depths = [-3.0, -1.0, 1.0, 3.0]
    assert set(np.unique(result.depth_map(depths))) <= set(depths)


def test_power_two_size_matches_the_plugin():
    assert edf.power_two_size(499) == (9, 512)
    assert edf.power_two_size(363) == (9, 512)
    assert edf.power_two_size(680) == (10, 1024)
    assert edf.power_two_size(116) == (7, 128)
    assert edf.power_two_size(512) == (9, 512)


def test_mirror_index_does_not_repeat_the_edge():
    assert list(edf.mirror_index(np.arange(-3, 8), 5)) == [3, 2, 1, 0, 1, 2, 3, 4, 3, 2, 1]
