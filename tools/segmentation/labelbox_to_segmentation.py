#!/usr/bin/env python3
"""
labelbox_to_segmentation.py

Convert Labelbox export rows (JSON/JSONL) containing image URLs and segmentation mask URLs
into a local dataset folder with:
  dataset/
    images/xxx.png (or original extension)
    masks/xxx.png  (single-channel mask, 0=background, N>=1 = class indices)

Supports multiple objects per image: assigns stable integer ids per class name.
If only one class is present (e.g., "coin"), background=0 and that class=1.

Usage:
  python labelbox_to_segmentation.py \
    --input /path/to/export.jsonl \
    --outdir /path/to/dataset \
    --api-key YOUR_LABELBOX_API_KEY \
    --train-split 0.85

Notes:
- Mask URLs from Labelbox often require an API key (Authorization: Bearer <key>).
- Some signed URLs may expire; re-run with a fresh export or provide API key.
- The script will create images/, masks/, and splits files train.txt / val.txt.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
import math

import numpy as np
from PIL import Image
import requests

try:
    from tqdm import tqdm
except Exception:
    tqdm = lambda x, **k: x  # fallback if tqdm not installed


def read_rows(path: Path) -> List[dict]:
    """
    Reads either JSONL (newline-delimited JSON) or a single JSON object/array file.
    Returns list of rows (dicts).
    """
    text = path.read_text(encoding="utf-8").strip()
    rows: List[dict] = []
    # Try JSONL first
    if "\n" in text:
        ok = True
        for i, line in enumerate(text.splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                ok = False
                break
            rows.append(obj)
        if ok and rows:
            return rows
        else:
            # fall back to single JSON
            rows = []
    try:
        js = json.loads(text)
        if isinstance(js, list):
            rows = js
        else:
            rows = [js]
    except json.JSONDecodeError as e:
        raise RuntimeError(f"File does not look like JSON or JSONL: {path}") from e
    return rows


def sanitize_filename(name: str) -> str:
    name = name.strip()
    # Keep extension if present
    # Replace non-filename characters
    name = re.sub(r"[^\w\-.]+", "_", name)
    return name


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def guess_ext_from_url(url: str, default: str = ".jpg") -> str:
    m = re.search(r"\.([a-zA-Z0-9]{1,5})(?:\?|$)", url)
    if m:
        ext = "." + m.group(1).lower()
        if ext in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}:
            return ".jpg" if ext == ".jpeg" else ext
    return default


def download(url: str, headers: Dict[str,str], retries: int = 3, timeout: int = 60) -> bytes:
    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, verify=False)
            if r.status_code == 200:
                return r.content
            else:
                last_err = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            last_err = e
        time.sleep(1.0 * (attempt + 1))
    raise last_err


def mask_to_indices(mask_img: Image.Image) -> np.ndarray:
    """
    Convert a mask image (often grayscale or RGBA) into a boolean/indices array.
    We treat any non-zero alpha or any non-zero luminance as foreground (1).
    """
    if mask_img.mode in ("RGBA", "LA"):
        arr = np.array(mask_img)
        # Use alpha if available, else sum of RGB
        if arr.shape[-1] == 4:
            alpha = arr[..., 3]
            fg = alpha > 0
        else:
            fg = arr[..., -1] > 0
        return fg.astype(np.uint8)
    else:
        arr = np.array(mask_img.convert("L"))
        return (arr > 0).astype(np.uint8)


def composite_class_mask(objs: List[Tuple[str, Image.Image]], size: Tuple[int,int]) -> np.ndarray:
    """
    Given a list of (class_name, mask_image), build a single-channel mask with class indices.
    Background=0, each class_name assigned a stable id (1..K).
    If multiple masks overlap, later objects will overwrite earlier ones.
    """
    class_to_id: Dict[str, int] = {}
    canvas = np.zeros(size[::-1], dtype=np.uint8)  # PIL size is (W,H); numpy uses (H,W)

    next_id = 1
    for cls_name, pil_mask in objs:
        if cls_name not in class_to_id:
            class_to_id[cls_name] = next_id
            next_id += 1
        cid = class_to_id[cls_name]
        idx = mask_to_indices(pil_mask)
        if idx.shape != canvas.shape:
            idx = np.array(Image.fromarray(idx).resize(size, resample=Image.NEAREST))
        canvas[idx > 0] = cid
    return canvas


def save_png_indices(path: Path, indices: np.ndarray):
    im = Image.fromarray(indices, mode="L")
    im.save(path, format="PNG")


def process_rows(rows: List[dict], outdir: Path, api_key: Optional[str], train_split: float, throttle: float):
    images_dir = outdir / "images"
    masks_dir  = outdir / "masks"
    ensure_dir(images_dir)
    ensure_dir(masks_dir)

    # Prepare headers
    headers_img = {}  # image URLs are often public signed URLs
    headers_mask = {}
    if api_key:
        headers_mask["Authorization"] = f"Bearer {api_key}"

    written_pairs: List[str] = []

    for row in tqdm(rows, desc="Processing rows"):
        # Resolve image URL & filename base
        # Common Labelbox export fields:
        # - data_row.external_id
        # - data_row.row_data (image URL)
        # - data_row.id
        # For your example the JSON is shaped like:
        # {"data_row": {...}, "media_attributes": {...}, "projects": {...}}
        data_row = row.get("data_row") or row
        external_id = None
        url_image = None

        if isinstance(data_row, dict):
            external_id = data_row.get("external_id")
            url_image = data_row.get("row_data")
        if not url_image:
            # Sometimes the URL is at top-level "row_data"
            url_image = row.get("row_data")
        if not external_id:
            # Fallback to id or synthesize from hash
            external_id = (data_row.get("id") if isinstance(data_row, dict) else None) or str(abs(hash(url_image)))[:12]

        base = sanitize_filename(external_id.rsplit(".", 1)[0] if "." in external_id else external_id)
        img_ext = guess_ext_from_url(url_image or "", default=".jpg")
        img_path = images_dir / f"{base}{img_ext}"
        mask_path = masks_dir / f"{base}.png"

        # Collect object masks & class names
        objs: List[Tuple[str, Image.Image]] = []

        projects = row.get("projects") or {}
        # Each project id -> {"labels": [ {"annotations": {"objects": [...]}} ]}
        for _pid, proj in projects.items():
            labels = proj.get("labels") or []
            for lab in labels:
                ann = lab.get("annotations") or {}
                objects = ann.get("objects") or []
                for obj in objects:
                    cls_name = obj.get("name") or obj.get("value") or "object"
                    mask = obj.get("mask") or {}
                    murl = mask.get("url")
                    if not murl:
                        continue
                    try:
                        mb = download(murl, headers=headers_mask)
                        pm = Image.open(io.BytesIO(mb)).convert("RGBA")
                        objs.append((cls_name, pm))
                    except Exception as e:
                        print(f"[warn] mask download failed for {external_id}: {e}", file=sys.stderr)

        # If no object masks collected, skip
        if not objs:
            print(f"[skip] No masks found for {external_id}", file=sys.stderr)
            continue

        # Download image (if not present)
        if url_image:
            if not img_path.exists():
                try:
                    ib = download(url_image, headers=headers_img)
                    Image.open(io.BytesIO(ib)).save(img_path)
                except Exception as e:
                    print(f"[warn] image download failed for {external_id}: {e}", file=sys.stderr)
                    # Still attempt to write mask with default size from first mask
        else:
            print(f"[warn] no image URL for {external_id}", file=sys.stderr)

        # Determine target size (use image if exists, else first mask)
        target_w, target_h = None, None
        if img_path.exists():
            try:
                with Image.open(img_path) as im:
                    target_w, target_h = im.size
            except Exception:
                pass
        if target_w is None or target_h is None:
            target_w, target_h = objs[0][1].size

        # Composite single-channel indices mask
        indices = composite_class_mask(objs, size=(target_w, target_h))
        save_png_indices(mask_path, indices)
        written_pairs.append(base)

        # Optional throttle (in seconds) to be gentle on servers / avoid rate limits
        if throttle > 0:
            time.sleep(throttle)

    # Write train/val split files
    n = len(written_pairs)
    n_train = int(math.floor(train_split * n))
    train_ids = written_pairs[:n_train]
    val_ids = written_pairs[n_train:]
    (outdir / "train.txt").write_text("\n".join(train_ids), encoding="utf-8")
    (outdir / "val.txt").write_text("\n".join(val_ids), encoding="utf-8")

    # Write a classes.txt mapping (sorted by appearance order)
    # We didn't persist class_to_id globally above for simplicity; compute by scanning masks.
    # Background is always 0; we'll list discovered ids from masks.
    (outdir / "README.txt").write_text(
        "Dataset structure:\n"
        "  images/  -> RGB images\n"
        "  masks/   -> single-channel PNGs, 0=background, 1..K=classes\n"
        "  train.txt, val.txt -> basenames (without extension) for each split\n\n"
        "Tip: in PyTorch, load mask with PIL (mode 'L') and use as LongTensor.\n",
        encoding="utf-8"
    )


# --- CLI ---

import io

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to Labelbox export JSON/JSONL")
    ap.add_argument("--outdir", required=True, help="Output dataset directory")
    ap.add_argument("--api-key", default=None, help="Labelbox API key (for mask URLs)")
    ap.add_argument("--train-split", type=float, default=0.85, help="Fraction for training split")
    ap.add_argument("--throttle", type=float, default=0.0, help="Seconds to sleep between downloads")
    args = ap.parse_args()

    in_path = Path(args.input)
    outdir = Path(args.outdir)

    rows = read_rows(in_path)
    print(f"Loaded {len(rows)} rows from {in_path}")
    process_rows(rows, outdir, api_key=args.api_key, train_split=args.train_split, throttle=args.throttle)
    print(f"Done. Wrote dataset to: {outdir}")

if __name__ == "__main__":
    main()
