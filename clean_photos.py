#!/usr/bin/env python3
"""Crop light borders from photographed prints and make cleaned copies.

Original files are never changed. The input and output folders default to
``photos`` and ``cleaned-photos`` so the workflow stays portable and private.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"}


def border_crop(image: np.ndarray) -> np.ndarray:
    """Remove only continuous, near-white outer lines from a photo.

    The small cap prevents a bright sky or wall inside a normal photograph
    from being mistaken for a border.
    """

    h, w = image.shape[:2]
    top, bottom, left, right = 0, h, 0, w

    def is_light(line: np.ndarray) -> bool:
        pixel = line.reshape(-1, 3).astype(np.int16)
        near_white = (pixel.min(axis=1) >= 238) & ((pixel.max(axis=1) - pixel.min(axis=1)) <= 18)
        return float(near_white.mean()) >= 0.985

    limit_y, limit_x = max(1, int(h * 0.03)), max(1, int(w * 0.03))
    while top < min(limit_y, bottom - 1) and is_light(image[top]):
        top += 1
    while h - bottom < limit_y and bottom > top + 1 and is_light(image[bottom - 1]):
        bottom -= 1
    while left < min(limit_x, right - 1) and is_light(image[:, left]):
        left += 1
    while w - right < limit_x and right > left + 1 and is_light(image[:, right - 1]):
        right -= 1
    return image[top:bottom, left:right]


def enhance(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    lightness = cv2.createCLAHE(clipLimit=1.35, tileGridSize=(8, 8)).apply(lightness)
    result = cv2.cvtColor(cv2.merge((lightness, a_channel, b_channel)), cv2.COLOR_LAB2BGR)
    blur = cv2.GaussianBlur(result, (0, 0), 0.8)
    return cv2.addWeighted(result, 1.12, blur, -0.12, 0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("photos"))
    parser.add_argument("--output", type=Path, default=Path("cleaned-photos"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in args.input.iterdir() if path.is_file() and path.suffix in IMAGE_EXTENSIONS)
    if not files:
        raise SystemExit(f"No supported images found in {args.input}")

    for source in files:
        image = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if image is None:
            print(f"skip {source.name}: unable to read")
            continue
        cleaned = enhance(border_crop(image))
        destination = args.output / f"{source.stem}.jpg"
        cv2.imwrite(str(destination), cleaned, [cv2.IMWRITE_JPEG_QUALITY, 96])
        print(f"{source.name} -> {destination}")


if __name__ == "__main__":
    main()
