"""The complex wavelet transform: exact inverse, and the same numbers as the EPFL plugin's Java code."""

from __future__ import annotations

import numpy as np
import pytest

from app.imaging import complex_wavelet as cw

DUMPS = ["wavelet_64x48_s1_l14", "wavelet_64x48_s2_l14", "wavelet_32x32_s3_l6", "wavelet_64x64_s2_l22"]


def lcg_image(nx: int, ny: int) -> np.ndarray:
    """The deterministic image ``WaveletCheck.java`` builds (a linear congruential generator, mod 256)."""
    seed = 12345
    image = np.zeros((ny, nx))
    for y in range(ny):
        for x in range(nx):
            seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
            image[y, x] = seed % 256
    return image


def load_dump(path):
    with open(path) as handle:
        nx, ny, scales, length, _ = handle.readline().split()
        rows = np.loadtxt(handle)
    nx, ny = int(nx), int(ny)
    values = rows.reshape(ny, nx, 3)
    return nx, ny, int(scales), int(length), values[..., 0], values[..., 1], values[..., 2]


@pytest.mark.parametrize("length", [6, 14, 22])
@pytest.mark.parametrize("scales", [1, 2, 4])
def test_synthesis_inverts_analysis(length, scales):
    image = np.random.default_rng(length * 10 + scales).uniform(0, 255, (96, 128))
    re, im = cw.analysis(image, scales, length)
    assert np.abs(cw.synthesis(re, im, scales, length) - image).max() < 1e-6


def test_sides_must_divide_by_the_scale():
    with pytest.raises(ValueError):
        cw.analysis(np.zeros((48, 40)), 4)


@pytest.mark.parametrize("name", DUMPS)
def test_transform_matches_plugin(edf_reference, name):
    nx, ny, scales, length, java_re, java_im, java_out = load_dump(edf_reference / "wavelet" / f"{name}.txt")
    re, im = cw.analysis(lcg_image(nx, ny), scales, length)
    assert np.abs(re - java_re).max() < 1e-9
    assert np.abs(im - java_im).max() < 1e-9
    assert np.abs(cw.synthesis(java_re, java_im, scales, length) - java_out).max() < 1e-9
