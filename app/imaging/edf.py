"""Extended depth of field: one image in focus everywhere, from a focal stack.

Two methods, both following the EPFL "Extended Depth of Field" ImageJ plugin (Forster, Van De Ville, Berent,
Sage and Unser, 2004, Microscopy Research and Technique 65:33-42, doi:10.1002/jemt.20092), whose Java source
was read for every step below:

**Variance selection** (the plugin's "low-medium" preset). Each plane's sharpness is the local variance in a
5 x 5 window (mirror boundaries, float32 arithmetic in the plugin's order); each pixel takes the plane of
greatest variance. The result is the height map (1-based plane index) and the pixels of the chosen planes.

**Complex wavelet fusion** (the plugin's "high" preset). Every plane is decomposed with the complex wavelet
transform of ``complex_wavelet.py`` (length 14, as many scales as the size allows); at each coefficient the
plane of greatest modulus wins; two consistency checks make the choices agree across the three detail
sub-bands of a position and, by a 5 x 5 majority vote, with their neighbours, on the three finest scales;
the inverse transform of the chosen coefficients is the composite; finally every pixel is reassigned to the
stack value nearest to the composite, which gives the height map and keeps only real, measured pixels.

Colour stacks are fused on their luminance (fixed weights 0.299, 0.587, 0.114, truncated to an integer as
the plugin does) and the colour composite takes each pixel from the plane the height map names.

Sizes that are not powers of two are padded, centred, with zeros to the plugin's power-of-two size and
cropped back. Large images are processed in overlapping tiles (``fuse``) so memory stays bounded; each tile
writes only the region it is responsible for, away from its borders.

One deliberate difference from the plugin: both consistency checks in the plugin take the image height as
the x extent and the width as the y extent (``nx = getHeight()``), so on a non-square padded size they visit
regions that are not the sub-bands. ``plugin_axes=True`` reproduces that (it is how the port is proven
exact against the plugin's own output); the default uses the true sub-band geometry.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import sobel

from app.imaging import complex_wavelet as cw

LUMA_WEIGHTS = (0.299, 0.587, 0.114)
VARIANCE_WINDOW = 5
MAJORITY_WINDOW = 5
CONSISTENCY_SCALES = 3
WAVELET_LENGTH = 14
TILE = 1024
MARGIN = 128
#: Seconds the parallel fusion waits for any window before it declares its processes stalled (a window of eleven
#: planes takes seconds; a pool process was once seen hanging at start-up on Windows, 2026-09-29).
STALL_S = 1200
COEFFICIENT_BUDGET_BYTES = 512 * 1_000_000

METHOD_VARIANCE = "variance"
METHOD_WAVELET = "complex-wavelet"


@dataclass
class EdfResult:
    """A composite and the map of where each of its pixels came from."""

    composite: np.ndarray  # (H, W, 3) uint8 for colour stacks, (H, W) float32 for grey stacks
    height_map: np.ndarray  # (H, W) uint16, 1-based index of the plane each pixel was taken from
    method: str
    parameters: dict = field(default_factory=dict)

    def depth_map(self, depths_um: list[float]) -> np.ndarray:
        """The height map expressed as focal depth in micrometres, from each plane's depth."""
        table = np.asarray(depths_um, dtype=np.float32)
        return table[self.height_map.astype(np.intp) - 1]


# --- helpers shared by both methods ---------------------------------------------------------------------


def luminance(rgb: np.ndarray) -> np.ndarray:
    """Grey value of 8-bit RGB pixels as the plugin computes it: weighted sum, truncated to an integer."""
    rgb = np.asarray(rgb)
    r = rgb[..., 0].astype(np.float64)
    g = rgb[..., 1].astype(np.float64)
    b = rgb[..., 2].astype(np.float64)
    wr, wg, wb = LUMA_WEIGHTS
    return np.floor(wr * r + wg * g + wb * b)


def power_two_size(n: int) -> tuple[int, int]:
    """(scales, padded size) for one side, as ``Tools.computeScaleAndPowerTwoSize`` computes them."""
    scales, length = 0, n
    while length > 1:
        scales += 1
        length = length // 2 if length % 2 == 0 else (length + 1) // 2
    return scales, length << scales


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def mirror_index(index: np.ndarray, n: int) -> np.ndarray:
    """ImageWare's MIRROR boundary: reflection without repeating the edge sample (period 2n - 2)."""
    index = np.asarray(index)
    if n <= 1:
        return np.zeros_like(index)
    period = 2 * n - 2
    index = np.mod(index, period)
    return np.where(index >= n, period - index, index)


def _mirror_pad(x: np.ndarray, half: int) -> np.ndarray:
    h, w = x.shape
    rows = mirror_index(np.arange(-half, h + half), h)
    cols = mirror_index(np.arange(-half, w + half), w)
    return x[np.ix_(rows, cols)]


def tenengrad(grey: np.ndarray) -> float:
    """Sharpness: the mean squared Sobel gradient magnitude."""
    g = np.asarray(grey, dtype=np.float64)
    gx = sobel(g, axis=1, mode="reflect")
    gy = sobel(g, axis=0, mode="reflect")
    return float(np.mean(gx * gx + gy * gy))


# --- variance selection -----------------------------------------------------------------------------------


def local_variance(plane: np.ndarray, window: int = VARIANCE_WINDOW) -> np.ndarray:
    """Variance in a ``window`` x ``window`` neighbourhood, float32, summed in the plugin's order.

    The plugin copies the neighbourhood with the x offset outermost and the y offset innermost, then sums
    the values, divides by the count, and sums the squared deviations, all in single precision.
    """
    x = np.asarray(plane, dtype=np.float32)
    h, w = x.shape
    half = window // 2
    padded = _mirror_pad(x, half)
    total = np.zeros((h, w), dtype=np.float32)
    for dx in range(window):
        for dy in range(window):
            total += padded[dy:dy + h, dx:dx + w]
    mean = total / np.float32(window * window)
    variance = np.zeros((h, w), dtype=np.float32)
    for dx in range(window):
        for dy in range(window):
            deviation = padded[dy:dy + h, dx:dx + w] - mean
            variance += deviation * deviation
    return variance


def variance_height_map(grey_stack: np.ndarray, window: int = VARIANCE_WINDOW) -> np.ndarray:
    """1-based index of the plane with the greatest local variance; ties keep the earlier plane."""
    nz, h, w = grey_stack.shape
    best = np.zeros((h, w), dtype=np.float32)
    height = np.ones((h, w), dtype=np.int32)
    for k in range(nz):
        v = local_variance(grey_stack[k], window)
        take = best < v
        best[take] = v[take]
        height[take] = k + 1
    return height


# --- complex wavelet fusion -------------------------------------------------------------------------------


def _read(values: np.ndarray, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
    """Values at (x, y); zero outside the array, as ImageWare's getPixel returns."""
    h, w = values.shape
    inside = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    out = np.zeros(xs.shape, dtype=values.dtype)
    out[inside] = values[ys[inside], xs[inside]]
    return out


def _write(values: np.ndarray, xs: np.ndarray, ys: np.ndarray, new: np.ndarray) -> None:
    """Write at (x, y); positions outside the array are dropped, as ImageWare's putPixel does."""
    h, w = values.shape
    inside = (xs >= 0) & (xs < w) & (ys >= 0) & (ys < h)
    values[ys[inside], xs[inside]] = new[inside]


def subband_consistency(height: np.ndarray, coeff_re: np.ndarray, coeff_im: np.ndarray,
                        extent_x: int, extent_y: int) -> None:
    """Make the three detail sub-bands of each position agree on one plane (in place).

    For the position's coefficients a (top right), b (bottom right) and c (bottom left): when two agree the
    third follows them; when all three differ, the plane of the coefficient with the greatest modulus wins
    in all three, and an exact tie leaves them as they are.
    """
    modulus = coeff_re.astype(np.float64) ** 2 + coeff_im.astype(np.float64) ** 2
    for scale in range(CONSISTENCY_SCALES):
        mx = extent_x >> scale
        my = extent_y >> scale
        if mx < 2 or my < 2:
            break
        xs, ys = np.meshgrid(np.arange(mx // 2, mx), np.arange(0, my // 2))
        pos_a = (xs, ys)
        pos_b = (xs, ys + my // 2)
        pos_c = (xs - mx // 2, ys + my // 2)
        a, b, c = _read(height, *pos_a), _read(height, *pos_b), _read(height, *pos_c)
        va, vb, vc = _read(modulus, *pos_a), _read(modulus, *pos_b), _read(modulus, *pos_c)
        new_a, new_b, new_c = a.copy(), b.copy(), c.copy()
        ab, ac, bc = a == b, a == c, b == c
        m = ab & ~ac
        new_c[m] = a[m]
        m = ~ab & ac
        new_b[m] = a[m]
        m = ~ab & ~ac & bc
        new_a[m] = b[m]
        differ = ~ab & ~ac & ~bc
        win_a = differ & (va > vb) & (va > vc)
        win_b = differ & ~win_a & (vb > va) & (vb > vc)
        win_c = differ & ~win_a & ~win_b & (vc > va) & (vc > vb)
        new_c[win_a] = a[win_a]
        new_b[win_a] = a[win_a]
        new_c[win_b] = b[win_b]
        new_a[win_b] = b[win_b]
        new_b[win_c] = c[win_c]
        new_a[win_c] = c[win_c]
        _write(height, *pos_a, new_a)
        _write(height, *pos_b, new_b)
        _write(height, *pos_c, new_c)


def majority_filter(block: np.ndarray, planes: int, window: int = MAJORITY_WINDOW) -> np.ndarray:
    """Each value becomes the plane held by more than half of its window, if one is; mirror boundaries."""
    h, w = block.shape
    half = window // 2
    size = window * window
    padded = _mirror_pad(block, half)
    views = np.stack([padded[dy:dy + h, dx:dx + w] for dx in range(window) for dy in range(window)])
    candidate = np.sort(views, axis=0)[size // 2]  # a value held by more than half sits in the middle
    count = (views == candidate).sum(axis=0)
    valid = (count > size // 2) & (candidate >= 0) & (candidate < planes)
    return np.where(valid, candidate, block)


def majority_consistency(height: np.ndarray, planes: int, extent_x: int, extent_y: int) -> None:
    """The majority vote on each detail sub-band of the three finest scales (in place)."""
    h, w = height.shape
    for subband in range(3):
        for scale in range(CONSISTENCY_SCALES):
            mx = (extent_x >> scale) // 2
            my = (extent_y >> scale) // 2
            if mx < 1 or my < 1:
                break
            x0, y0 = {0: (0, my), 1: (mx, 0), 2: (mx, my)}[subband]
            block = np.zeros((my, mx), dtype=height.dtype)
            x1, y1 = min(x0 + mx, w), min(y0 + my, h)
            if x0 >= w or y0 >= h:
                continue  # entirely outside: the plugin reads zeros and writes nothing back
            block[: y1 - y0, : x1 - x0] = height[y0:y1, x0:x1]
            filtered = majority_filter(block, planes)
            height[y0:y1, x0:x1] = filtered[: y1 - y0, : x1 - x0]


def _merged_coefficients(grey_stack: np.ndarray, scales: int, length: int, subband: bool, majority: bool,
                         plugin_axes: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Coefficient selection on a stack whose sides are divisible by 2**scales."""
    nz, h, w = grey_stack.shape
    checks = subband or majority
    keep_stack = checks and nz * h * w * 8 <= COEFFICIENT_BUDGET_BYTES
    best = np.zeros((h, w), dtype=np.float32)
    height = np.zeros((h, w), dtype=np.int32)
    res_re = np.zeros((h, w), dtype=np.float32)
    res_im = np.zeros((h, w), dtype=np.float32)
    stack_re = np.empty((nz, h, w), dtype=np.float32) if keep_stack else None
    stack_im = np.empty((nz, h, w), dtype=np.float32) if keep_stack else None
    for k in range(nz):
        re, im = cw.analysis(grey_stack[k], scales, length)
        modulus = re * re + im * im
        take = best.astype(np.float64) < modulus
        best[take] = modulus[take]
        height[take] = k
        res_re[take] = re[take]
        res_im[take] = im[take]
        if keep_stack:
            stack_re[k] = re
            stack_im[k] = im
    if not checks:
        return res_re, res_im, height
    extent_x, extent_y = (h, w) if plugin_axes else (w, h)
    if subband:
        subband_consistency(height, res_re, res_im, extent_x, extent_y)
    if majority:
        majority_consistency(height, nz, extent_x, extent_y)
    if keep_stack:
        index = height[None, :, :]
        res_re = np.take_along_axis(stack_re, index, axis=0)[0]
        res_im = np.take_along_axis(stack_im, index, axis=0)[0]
    else:  # second pass: recompute each plane's coefficients and keep them where that plane was chosen
        for k in range(nz):
            chosen = height == k
            if chosen.any():
                re, im = cw.analysis(grey_stack[k], scales, length)
                res_re[chosen] = re[chosen]
                res_im[chosen] = im[chosen]
    return res_re, res_im, height


def reassign(composite: np.ndarray, grey_stack: np.ndarray) -> np.ndarray:
    """1-based index of the plane whose value is nearest the composite; ties keep the earlier plane."""
    target = np.asarray(composite, dtype=np.float32).astype(np.float64)
    nz, h, w = grey_stack.shape
    best = np.full((h, w), np.inf)
    height = np.ones((h, w), dtype=np.int32)
    for k in range(nz):
        distance = np.abs(grey_stack[k].astype(np.float64) - target)
        take = distance < best
        best[take] = distance[take]
        height[take] = k + 1
    return height


def wavelet_height_map(grey_stack: np.ndarray, length: int = WAVELET_LENGTH, scales: int | None = None,
                       subband: bool = True, majority: bool = True, plugin_axes: bool = False) -> np.ndarray:
    """The plugin's "high" pipeline on one block: pad, fuse, synthesise, crop, reassign."""
    grey_stack = np.asarray(grey_stack, dtype=np.float64)
    nz, ny, nx = grey_stack.shape
    sx, px = power_two_size(nx)
    sy, py = power_two_size(ny)
    max_scales = min(sx, sy)
    if scales is None:
        scales = max(max_scales, 1)
    if _is_power_of_two(nx) and _is_power_of_two(ny):
        mx, my = nx, ny
    else:
        mx, my = px, py
    a, b = (mx - nx) // 2, (my - ny) // 2
    padded = np.zeros((nz, my, mx), dtype=np.float64)
    padded[:, b:b + ny, a:a + nx] = grey_stack
    res_re, res_im, _ = _merged_coefficients(padded, scales, length, subband, majority, plugin_axes)
    composite = cw.synthesis(res_re.astype(np.float64), res_im.astype(np.float64), scales, length)
    composite = composite.astype(np.float32)[b:b + ny, a:a + nx]
    return reassign(composite, grey_stack)


# --- the driver: stacks of any size, colour or grey -------------------------------------------------------

PlaneReader = Callable[[int, int, int, int, int], np.ndarray]
"""``read(k, x, y, w, h)`` returns plane ``k``'s window: (h, w, 3) uint8 or (h, w) grey."""


def _tile_windows(size: int, tile: int, margin: int) -> list[tuple[int, int, int, int]]:
    """(window start, window length, own start, own end) along one axis."""
    if size <= tile:
        return [(0, size, 0, size)]
    core = tile - 2 * margin
    windows = []
    for own_start in range(0, size, core):
        own_end = min(own_start + core, size)
        start = min(max(own_start - margin, 0), size - tile)
        windows.append((start, tile, own_start, own_end))
    return windows


def window_height_map(stack: np.ndarray, method: str, plugin_axes: bool = False) -> np.ndarray:
    """The height map of one window's stack (planes, h, w[, 3]); a process of the fusion's pool runs it."""
    grey = luminance(stack) if stack.ndim == 4 else stack.astype(np.float64)
    if method == METHOD_WAVELET:
        return wavelet_height_map(grey, plugin_axes=plugin_axes)
    return variance_height_map(grey)


def fuse(read: PlaneReader, planes: int, width: int, height: int, method: str = METHOD_WAVELET,
         tile: int = TILE, margin: int = MARGIN, plugin_axes: bool = False,
         progress: Callable[[int, int], None] | None = None, workers: int = 1,
         stall_s: float = STALL_S) -> EdfResult:
    """Fuse a focal stack of ``planes`` planes, reading windows through ``read``.

    The windows are independent: each owns its core and writes only there. With ``workers`` above 1 their height
    maps are computed in that many processes while this one reads the windows (the images it reads from stay
    here) and assembles them, which gives the same arrays as one window at a time. At most two windows per worker
    are in flight, so memory stays bounded whatever the stack's size.
    """
    if planes < 1:
        raise ValueError("a focal stack needs at least one plane")
    if method not in (METHOD_WAVELET, METHOD_VARIANCE):
        raise ValueError(f"unknown method {method!r}")
    height_map = np.zeros((height, width), dtype=np.uint16)
    composite = None
    windows = [(xw, yw) for yw in _tile_windows(height, tile, margin) for xw in _tile_windows(width, tile, margin)]

    def read_window(spec) -> np.ndarray:
        (x0, tw, _, _), (y0, th, _, _) = spec
        return np.stack([np.asarray(read(k, x0, y0, tw, th)) for k in range(planes)])

    def place(spec, stack: np.ndarray, local: np.ndarray) -> None:
        nonlocal composite
        (x0, _, ox0, ox1), (y0, _, oy0, oy1) = spec
        own = local[oy0 - y0:oy1 - y0, ox0 - x0:ox1 - x0]
        height_map[oy0:oy1, ox0:ox1] = own
        index = (own.astype(np.intp) - 1)[None, ...]
        if stack.ndim == 4:
            if composite is None:
                composite = np.zeros((height, width, 3), dtype=np.uint8)
            window = stack[:, oy0 - y0:oy1 - y0, ox0 - x0:ox1 - x0, :]
            composite[oy0:oy1, ox0:ox1] = np.take_along_axis(window, index[..., None], axis=0)[0]
        else:
            if composite is None:
                composite = np.zeros((height, width), dtype=np.float32)
            window = stack[:, oy0 - y0:oy1 - y0, ox0 - x0:ox1 - x0].astype(np.float32)
            composite[oy0:oy1, ox0:ox1] = np.take_along_axis(window, index, axis=0)[0]

    workers = max(1, min(int(workers), len(windows)))
    if workers == 1:
        for done, spec in enumerate(windows):
            stack = read_window(spec)
            place(spec, stack, window_height_map(stack, method, plugin_axes))
            if progress:
                progress(done + 1, len(windows))
    else:
        import multiprocessing
        from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait

        done = 0
        pool = ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn"))
        stalled = False
        try:
            pending: dict = {}
            upcoming = iter(windows)
            exhausted = False
            while pending or not exhausted:
                while not exhausted and len(pending) < 2 * workers:
                    spec = next(upcoming, None)
                    if spec is None:
                        exhausted = True
                        break
                    stack = read_window(spec)
                    pending[pool.submit(window_height_map, stack, method, plugin_axes)] = (spec, stack)
                finished, _ = wait(pending, timeout=stall_s, return_when=FIRST_COMPLETED)
                if not finished:
                    stalled = True
                    raise RuntimeError(f"no window of the fusion finished in {stall_s:.0f} s: its processes stalled")
                for future in finished:
                    spec, stack = pending.pop(future)
                    place(spec, stack, future.result())
                    done += 1
                    if progress:
                        progress(done, len(windows))
        finally:
            if stalled:
                # A stalled process never answers a shutdown: stop every one first.
                for process in list(getattr(pool, "_processes", {}).values()):
                    process.terminate()
                pool.shutdown(wait=False, cancel_futures=True)
            else:
                pool.shutdown(wait=True)
    parameters = {"tile": tile, "margin": margin, "planes": planes}
    if method == METHOD_WAVELET:
        parameters |= {"length": WAVELET_LENGTH, "subband_check": True, "majority_check": True,
                       "majority_window": MAJORITY_WINDOW, "plugin_axes": plugin_axes}
    else:
        parameters |= {"window": VARIANCE_WINDOW}
    return EdfResult(composite=composite, height_map=height_map, method=method, parameters=parameters)


def array_reader(stack: np.ndarray) -> PlaneReader:
    """A reader over an in-memory stack, (planes, H, W[, 3])."""

    def read(k: int, x: int, y: int, w: int, h: int) -> np.ndarray:
        return stack[k, y:y + h, x:x + w]

    return read


def fuse_array(stack: np.ndarray, method: str = METHOD_WAVELET, **options) -> EdfResult:
    """``fuse`` on an in-memory stack."""
    stack = np.asarray(stack)
    return fuse(array_reader(stack), stack.shape[0], stack.shape[2], stack.shape[1], method, **options)
