"""Synthetic focal stacks whose in-focus plane is known at every pixel.

A multi-scale random texture is the specimen; its surface is a tilted plane with a bump. Plane ``k`` shows
each pixel blurred by a Gaussian whose width grows with the distance between the surface and plane ``k``,
so the true in-focus plane of a pixel is its rounded surface height. Seeded, so every run is identical.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter


def texture(h: int, w: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = np.zeros((h, w))
    for sigma, weight in ((1, 0.5), (3, 1.0), (8, 1.0), (20, 0.8)):
        t += weight * gaussian_filter(rng.standard_normal((h, w)), sigma)
    t = (t - t.min()) / (t.max() - t.min())
    return 20 + 215 * t


def focal_stack(h: int, w: int, planes: int, seed: int, noise: float = 0.0):
    """(stack as 0-255 integers in float, the sharp specimen, the 1-based true plane of each pixel)."""
    sharp = texture(h, w, seed)
    yy, xx = np.mgrid[0:h, 0:w]
    surface = (planes - 1) * (0.15 + 0.7 * (xx / w * 0.6 + yy / h * 0.4))
    surface += 0.12 * planes * np.exp(-(((xx - 0.6 * w) / (0.2 * w)) ** 2 + ((yy - 0.4 * h) / (0.25 * h)) ** 2))
    surface = np.clip(surface, 0, planes - 1)
    widths = np.linspace(0, 1.4 * planes, 64)
    blurred = np.stack([sharp if s == 0 else gaussian_filter(sharp, s * 0.35) for s in widths])
    stack = np.empty((planes, h, w))
    for k in range(planes):
        level = np.clip(np.searchsorted(widths, np.abs(surface - k)), 0, len(widths) - 1)
        stack[k] = np.take_along_axis(blurred, level[None], 0)[0]
    if noise:
        stack += np.random.default_rng(seed + 100).normal(0, noise, stack.shape)
    return np.clip(np.round(stack), 0, 255), sharp, np.rint(surface).astype(int) + 1
