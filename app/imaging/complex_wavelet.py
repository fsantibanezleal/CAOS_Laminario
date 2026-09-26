"""The separable complex wavelet transform of Forster et al. (2004), as the EPFL plugin computes it.

A pair of real filter banks, one "real" (``h``, ``g``) and one "imaginary" (``hi``, ``gi``), each a
lowpass and a highpass, with periodic boundaries. One analysis step splits an array along one axis into
its lowpass half (first) and highpass half (second). The 2-D complex transform of an image at scale 1 is

    Re = split(x, re, re) - split(x, im, im)
    Im = split(x, re, im) + split(x, im, re)

where ``split(x, a, b)`` filters rows with bank ``a`` and columns with bank ``b``. Deeper scales apply the
same to the lowpass quadrant of both parts, mixing real and imaginary quadrants as the plugin does.
Synthesis is the exact inverse. The coefficients sit in the quadtree layout ImageJ uses: at each scale the
top-left quadrant holds the coarser approximation, the other three the details.

Filters of length 6, 14 and 22 are the plugin's tables (``wavelets/ComplexWaveFilter.java``), typed here
from that source; the plugin's "high quality" preset uses length 14.

The transform is written with NumPy on whole axes at once (``np.roll`` over periodic indices), which
gives the same numbers as the plugin's per-row loops.
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np

_H6 = [-0.0662912607, 0.1104854346, 0.6629126074, 0.6629126074, 0.1104854346, -0.0662912607]
_G6 = [-0.0662912607, -0.1104854346, 0.6629126074, -0.6629126074, 0.1104854346, 0.0662912607]
_HI6 = [-0.0855816496, -0.0855816496, 0.1711632992, 0.1711632992, -0.0855816496, -0.0855816496]
_GI6 = [0.0855816496, -0.0855816496, -0.1711632992, 0.1711632992, 0.0855816496, -0.0855816496]

_H14 = [0.0049120149, -0.0054111299, -0.0701089996, -0.0564377788, 0.1872348173, 0.3676385056, 0.2792793518,
        0.2792793518, 0.3676385056, 0.1872348173, -0.0564377788, -0.0701089996, -0.0054111299, 0.0049120149]
_G14 = [0.0049120149, 0.0054111299, -0.0701089996, 0.0564377788, 0.1872348173, -0.3676385056, 0.2792793518,
        -0.2792793518, 0.3676385056, -0.1872348173, -0.0564377788, 0.0701089996, -0.0054111299, -0.0049120149]
_HI14 = [0.0018464710, 0.0143947836, 0.0079040001, -0.1169376946, -0.2596312614, -0.0475928095, 0.4000165107,
         0.4000165107, -0.0475928095, -0.2596312614, -0.1169376946, 0.0079040001, 0.0143947836, 0.0018464710]
_GI14 = [-0.0018464710, 0.0143947836, -0.0079040001, -0.1169376946, 0.2596312614, -0.0475928095, -0.4000165107,
         0.4000165107, 0.0475928095, -0.2596312614, 0.1169376946, 0.0079040001, -0.0143947836, 0.0018464710]

_H22 = [-0.0002890832, -0.0000935982, 0.0059961342, 0.0122232015, -0.0243700791, -0.1092940542, -0.0918847036,
        0.1540094645, 0.4014277015, 0.3153022916, 0.0440795062, 0.0440795062, 0.3153022916, 0.4014277015,
        0.1540094645, -0.0918847036, -0.1092940542, -0.0243700791, 0.0122232015, 0.0059961342, -0.0000935982,
        -0.0002890832]
_G22 = [-0.0002890832, 0.0000935982, 0.0059961342, -0.0122232015, -0.0243700791, 0.1092940542, -0.0918847036,
        -0.1540094645, 0.4014277015, -0.3153022916, 0.0440795062, -0.0440795062, 0.3153022916, -0.4014277015,
        0.1540094645, 0.0918847036, -0.1092940542, 0.0243700791, 0.0122232015, -0.0059961342, -0.0000935982,
        0.0002890832]
_HI22 = [0.0000211708, -0.0012780664, -0.0029648612, 0.0144283733, 0.0503067404, -0.0044659104, -0.1999654035,
         -0.2603015239, 0.0013800055, 0.2232934469, 0.1795460286, 0.1795460286, 0.2232934469, 0.0013800055,
         -0.2603015239, -0.1999654035, -0.0044659104, 0.0503067404, 0.0144283733, -0.0029648612, -0.0012780664,
         0.0000211708]
_GI22 = [-0.0000211708, -0.0012780664, 0.0029648612, 0.0144283733, -0.0503067404, -0.0044659104, 0.1999654035,
         -0.2603015239, -0.0013800055, 0.2232934469, -0.1795460286, 0.1795460286, -0.2232934469, 0.0013800055,
         0.2603015239, -0.1999654035, 0.0044659104, 0.0503067404, -0.0144283733, -0.0029648612, 0.0012780664,
         0.0000211708]

FILTERS = {6: (_H6, _G6, _HI6, _GI6), 14: (_H14, _G14, _HI14, _GI14), 22: (_H22, _G22, _HI22, _GI22)}
RE, IM = 0, 1


@lru_cache
def bank(length: int, kind: int) -> tuple[np.ndarray, np.ndarray]:
    """The (lowpass, highpass) pair of the real (``RE``) or imaginary (``IM``) bank of a given length."""
    if length not in FILTERS:
        raise ValueError(f"filter length must be one of {sorted(FILTERS)}, not {length}")
    h, g, hi, gi = FILTERS[length]
    return (np.asarray(h), np.asarray(g)) if kind == RE else (np.asarray(hi), np.asarray(gi))


def _filter_periodic(x: np.ndarray, taps: np.ndarray, axis: int, forward: bool) -> np.ndarray:
    """y[i] = sum_k taps[k] * x[i + k - n/2] (forward) or x[i - k + n/2] (inverse), periodic in i."""
    out = np.zeros_like(x, dtype=np.float64)
    half = len(taps) // 2
    for k, tap in enumerate(taps):
        shift = (k - half) if forward else (half - k)
        # x[i + shift] == np.roll(x, -shift)[i]
        out += tap * np.roll(x, -shift, axis=axis)
    return out


def _split_axis(x: np.ndarray, low: np.ndarray, high: np.ndarray, axis: int) -> np.ndarray:
    """One analysis step along ``axis``: lowpass at even samples first, then highpass at even samples."""
    n = x.shape[axis]
    lo = _filter_periodic(x, low, axis, forward=True)
    hi = _filter_periodic(x, high, axis, forward=True)
    even = [slice(None)] * x.ndim
    even[axis] = slice(0, n, 2)
    return np.concatenate([lo[tuple(even)], hi[tuple(even)]], axis=axis)


def _merge_axis(v: np.ndarray, low: np.ndarray, high: np.ndarray, axis: int) -> np.ndarray:
    """One synthesis step along ``axis``: upsample both halves by zero insertion and filter."""
    n = v.shape[axis]
    n2 = n // 2
    first = [slice(None)] * v.ndim
    first[axis] = slice(0, n2)
    second = [slice(None)] * v.ndim
    second[axis] = slice(n2, n)
    up_lo = np.zeros_like(v, dtype=np.float64)
    up_hi = np.zeros_like(v, dtype=np.float64)
    even = [slice(None)] * v.ndim
    even[axis] = slice(0, 2 * n2, 2)
    up_lo[tuple(even)] = v[tuple(first)]
    up_hi[tuple(even)] = v[tuple(second)]
    return _filter_periodic(up_lo, low, axis, forward=False) + _filter_periodic(up_hi, high, axis, forward=False)


def _split(x: np.ndarray, rows: int, cols: int, length: int) -> np.ndarray:
    """Rows filtered with bank ``rows`` (axis 1), then columns with bank ``cols`` (axis 0)."""
    out = _split_axis(x, *bank(length, rows), axis=1)
    return _split_axis(out, *bank(length, cols), axis=0)


def _merge(v: np.ndarray, rows: int, cols: int, length: int) -> np.ndarray:
    out = _merge_axis(v, *bank(length, rows), axis=1)
    return _merge_axis(out, *bank(length, cols), axis=0)


def analysis(image: np.ndarray, scales: int, length: int = 14) -> tuple[np.ndarray, np.ndarray]:
    """The complex wavelet coefficients (real part, imaginary part) of a 2-D image, quadtree layout.

    ``image`` is (rows, columns) and each side must be divisible by 2**scales.
    """
    x = np.asarray(image, dtype=np.float64)
    ny, nx = x.shape
    if ny % (1 << scales) or nx % (1 << scales):
        raise ValueError(f"image {nx} x {ny} is not divisible by 2**{scales}")
    out_re = x.copy()
    out_im = x.copy()
    sub = out_re[:ny, :nx].copy()  # a copy: the real part is overwritten before the imaginary part is built
    out_re[:ny, :nx] = _split(sub, RE, RE, length) - _split(sub, IM, IM, length)
    out_im[:ny, :nx] = _split(sub, RE, IM, length) + _split(sub, IM, RE, length)
    ny //= 2
    nx //= 2
    for _ in range(1, scales):
        sub_re = out_re[:ny, :nx].copy()
        sub_im = out_im[:ny, :nx].copy()
        out_re[:ny, :nx] = (_split(sub_re, RE, RE, length) - _split(sub_re, IM, IM, length)
                            - _split(sub_im, RE, IM, length) - _split(sub_im, IM, RE, length))
        out_im[:ny, :nx] = (_split(sub_re, RE, IM, length) + _split(sub_re, IM, RE, length)
                            + _split(sub_im, RE, RE, length) - _split(sub_im, IM, IM, length))
        ny //= 2
        nx //= 2
    return out_re, out_im


def synthesis(coeff_re: np.ndarray, coeff_im: np.ndarray, scales: int, length: int = 14) -> np.ndarray:
    """The image whose coefficients these are (the real part of the reconstruction)."""
    out_re = np.asarray(coeff_re, dtype=np.float64).copy()
    out_im = np.asarray(coeff_im, dtype=np.float64).copy()
    div = 1 << (scales - 1)
    ny = out_re.shape[0] // div
    nx = out_re.shape[1] // div
    for _ in range(scales):
        sub_re = out_re[:ny, :nx].copy()
        sub_im = out_im[:ny, :nx].copy()
        out_re[:ny, :nx] = (_merge(sub_re, RE, RE, length) - _merge(sub_re, IM, IM, length)
                            + _merge(sub_im, RE, IM, length) + _merge(sub_im, IM, RE, length))
        out_im[:ny, :nx] = (_merge(sub_im, RE, RE, length) - _merge(sub_re, RE, IM, length)
                            - _merge(sub_re, IM, RE, length) - _merge(sub_im, IM, IM, length))
        ny *= 2
        nx *= 2
    return out_re
