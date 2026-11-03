"""Prepare baked cloth maps for a web viewer.

Input:  <src>/<key>-body-normal.png and <key>-body-ao.png (from cloth_bake.py, UV u shifted by -0.25)
Output: <dst>/<key>-normal.webp and <key>-ao.webp

Steps: undo the UV shift, blur ray-miss artefacts in deep folds, clamp and
re-normalise the normal map, and lift the AO floor so self-intersecting folds
never go fully black.

Usage:
    python -I postprocess_bake_maps.py <src_dir> <dst_dir> key1 [key2 ...]
"""
import pathlib
import sys

import numpy as np
from PIL import Image, ImageFilter

src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
keys = sys.argv[3:]
dst.mkdir(parents=True, exist_ok=True)

for key in keys:
    n = np.asarray(Image.open(src / f"{key}-body-normal.png").convert("RGB"), dtype=np.float32) / 255 * 2 - 1
    shift = n.shape[1] // 4  # u was shifted by -0.25 before baking
    n = np.roll(n, shift, axis=1)
    xy = n[..., :2]
    for c in range(2):
        ch = Image.fromarray(((xy[..., c] + 1) * 127.5).clip(0, 255).astype(np.uint8))
        xy[..., c] = np.asarray(ch.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 127.5 - 1
    xy = np.clip(xy * 0.9, -0.6, 0.6)
    z = np.sqrt(np.clip(1 - (xy ** 2).sum(-1), 0.2, 1))
    rgb = np.dstack([xy, z])
    rgb /= np.linalg.norm(rgb, axis=-1, keepdims=True)
    Image.fromarray(((rgb + 1) * 127.5).clip(0, 255).astype(np.uint8)).save(
        dst / f"{key}-normal.webp", quality=90, method=6)

    a = np.asarray(Image.open(src / f"{key}-body-ao.png").convert("L"), dtype=np.float32) / 255
    a = np.roll(a, shift, axis=1)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)),
                   dtype=np.float32) / 255
    a = 0.6 + 0.4 * a
    Image.fromarray((a * 255).clip(0, 255).astype(np.uint8)).save(dst / f"{key}-ao.webp", quality=85, method=6)
    print(key, "ok")
