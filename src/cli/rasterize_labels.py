from __future__ import annotations

import argparse
from pathlib import Path

from src.geo.rasterize import DEFAULT_LABEL_BUFFER_METERS, rasterize_labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rasterize vector labels into a binary mask aligned to a reference GeoTIFF."
    )
    parser.add_argument("--vectors", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--buffer-meters", type=float, default=DEFAULT_LABEL_BUFFER_METERS)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.vectors.exists():
        raise FileNotFoundError(f"vector file does not exist: {args.vectors}")
    if not args.reference.exists():
        raise FileNotFoundError(f"reference raster does not exist: {args.reference}")

    positive_pixels = rasterize_labels(
        args.vectors,
        args.reference,
        args.output,
        args.buffer_meters,
    )
    print(f"Wrote mask to {args.output} with {positive_pixels} positive pixels")


if __name__ == "__main__":
    main()
