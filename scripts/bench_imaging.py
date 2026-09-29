#!/usr/bin/env python3
"""Reproduce every measurement table of docs/architecture/04_imaging.md.

Needs libvips (``LAMINARIO_VIPS_BIN`` on Windows) and the fixtures (``LAMINARIO_FIXTURES``), both read from the
environment or the local ``.env``. Writes one JSON report and prints each table as it is measured. It writes
pyramids into ``--work`` (a scratch folder, removed at the end unless ``--keep``), never into the repository.

Usage: ``python scripts/bench_imaging.py --out E:/_Temp/laminario-bench [--work DIR] [--keep]``
"""

from __future__ import annotations

import argparse
import gc
import json
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import Settings  # noqa: E402
from app.imaging import edf, pyramid, reader  # noqa: E402
from app.imaging.library import vips  # noqa: E402
from tests.imaging.synthetic import focal_stack  # noqa: E402

CMU1_REGION = (12000, 8000, 6000, 5000)
GROUND_TRUTH_SIZES = [(128, 256, 12, 1), (170, 300, 16, 2), (256, 256, 16, 3), (420, 700, 20, 4), (500, 680, 24, 5)]


def pyramids(samples: Path, work: Path) -> list[dict]:
    rows = []
    for name in ("cmu1.svs", "nhm_lice_scan.tif", "commons_thin_xpl.jpg"):
        info = reader.read_info(samples / name)
        image = reader.open_plane(info)
        if name == "cmu1.svs":
            image = image.crop(*CMU1_REGION)
        megapixels = image.width * image.height / 1e6
        for codec in ("jpeg", "webp", "auto"):
            start = time.perf_counter()
            out = pyramid.write_pyramid(image, work / f"{name}.{codec}.tif", info.mpp_x, codec)
            rows.append(dict(file=name, asked=codec, chosen=out.codec, quality=out.quality, bytes=out.bytes,
                             kb_per_mp=round(out.bytes / megapixels / 1e3, 1), psnr_db=round(out.psnr_db, 2),
                             levels=out.levels, seconds=round(time.perf_counter() - start, 2)))
            print(f"  {name:22s} {codec:5s} -> {out.codec} Q{out.quality} {rows[-1]['kb_per_mp']:7.1f} KB/MP "
                  f"{out.psnr_db:6.2f} dB", flush=True)
    return rows


def quality_ladder(samples: Path, work: Path) -> list[dict]:
    module = vips()
    image = reader.open_plane(reader.read_info(samples / "commons_thin_xpl.jpg"))
    rows = []
    for quality in (85, 88, 90, 92, 95, 97):
        path = work / f"thin-q{quality}.tif"
        image.tiffsave(str(path), tile=True, pyramid=True, bigtiff=True, tile_width=512, tile_height=512,
                       compression="jpeg", Q=quality, keep="icc")
        score = pyramid.level0_psnr(image, module.Image.new_from_file(str(path)))
        rows.append(dict(quality=quality, megabytes=round(path.stat().st_size / 1e6, 2), psnr_db=round(score, 2)))
        print(f"  Q{quality}: {rows[-1]['megabytes']} MB {rows[-1]['psnr_db']} dB", flush=True)
    return rows


def edf_port(reference: Path) -> list[dict]:
    import tifffile
    from skimage.metrics import structural_similarity

    rows = []
    for case in ("dome", "eye", "skeleton"):
        stack = tifffile.imread(reference / case / "stack.tif")
        for preset, method in (("high", edf.METHOD_WAVELET), ("variance", edf.METHOD_VARIANCE)):
            height = tifffile.imread(reference / case / f"{preset}-heightmap.tif").astype(np.int32)
            composite = tifffile.imread(reference / case / f"{preset}-composite.tif")
            for axes in (True, False):
                start = time.perf_counter()
                result = edf.fuse_array(stack, method, plugin_axes=axes)
                seconds = time.perf_counter() - start
                if composite.ndim == 3:
                    ssim = structural_similarity(result.composite, composite, channel_axis=2, data_range=255)
                else:
                    span = float(composite.max() - composite.min())
                    ssim = structural_similarity(result.composite.astype(float), composite.astype(float),
                                                 data_range=span)
                rows.append(dict(stack=case, method=method, plugin_axes=axes,
                                 agreement=round(float(np.mean(result.height_map == height)), 5),
                                 ssim=round(float(ssim), 5), seconds=round(seconds, 2)))
                print(f"  {case:8s} {method:16s} plugin_axes={axes!s:5s} agreement {rows[-1]['agreement']:.5f} "
                      f"SSIM {rows[-1]['ssim']:.5f} {seconds:.1f} s", flush=True)
    return rows


def ground_truth(noise: float) -> list[dict]:
    rows = []
    for h, w, planes, seed in GROUND_TRUTH_SIZES:
        stack, sharp, truth = focal_stack(h, w, planes, seed, noise=noise)
        for label, method, axes in (("variance", edf.METHOD_VARIANCE, False),
                                    ("wavelet, plugin axes", edf.METHOD_WAVELET, True),
                                    ("wavelet, true axes", edf.METHOD_WAVELET, False)):
            result = edf.fuse_array(stack, method, plugin_axes=axes)
            within = float(np.mean(np.abs(result.height_map.astype(int) - truth) <= 1))
            rmse = float(np.sqrt(np.mean((result.composite.astype(float) - sharp) ** 2)))
            rows.append(dict(size=f"{w} x {h}", planes=planes, noise=noise, method=label,
                             within_one_plane=round(within, 4), composite_rmse=round(rmse, 3)))
            print(f"  {w}x{h} {planes:3d} planes noise {noise:3.0f} {label:22s} within-1 {within:.4f} "
                  f"RMSE {rmse:.3f}", flush=True)
    return rows


def tiling() -> list[dict]:
    stack, sharp, truth = focal_stack(700, 1300, 16, 7)
    rows = []
    for method in (edf.METHOD_VARIANCE, edf.METHOD_WAVELET):
        whole = edf.fuse_array(stack, method, tile=4096)
        tiled = edf.fuse_array(stack, method, tile=256, margin=64)
        rows.append(dict(method=method, agreement=round(float(np.mean(whole.height_map == tiled.height_map)), 4),
                         within_whole=round(float(np.mean(np.abs(whole.height_map.astype(int) - truth) <= 1)), 4),
                         within_tiled=round(float(np.mean(np.abs(tiled.height_map.astype(int) - truth) <= 1)), 4)))
        print(f"  {method:16s} {rows[-1]}", flush=True)
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path, help="folder for the JSON report")
    parser.add_argument("--work", type=Path, help="scratch folder for pyramids (default: <out>/work)")
    parser.add_argument("--keep", action="store_true", help="keep the written pyramids")
    args = parser.parse_args(argv)
    fixtures = Settings().fixtures
    if not fixtures or not Path(fixtures).is_dir():
        print("LAMINARIO_FIXTURES is not set to the data vault")
        return 2
    fixtures = Path(fixtures)
    work = args.work or args.out / "work"
    work.mkdir(parents=True, exist_ok=True)
    report = {"library": vips().version(0), "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print("pyramids")
    report["pyramids"] = pyramids(fixtures / "samples", work)
    print("thin section quality ladder")
    report["quality_ladder"] = quality_ladder(fixtures / "samples", work)
    print("EDF against the EPFL plugin")
    report["edf_port"] = edf_port(fixtures / "edf-reference")
    for noise in (0.0, 3.0, 8.0):
        print(f"EDF against known focus, noise {noise}")
        report[f"ground_truth_noise_{noise:g}"] = ground_truth(noise)
    print("tiled against whole")
    report["tiling"] = tiling()
    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / "bench-imaging.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {target}")
    if not args.keep:
        module = vips()
        module.cache_set_max(0)  # cached operations hold the pyramids open, and Windows cannot delete open files
        gc.collect()
        shutil.rmtree(work)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
