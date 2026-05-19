from __future__ import annotations

import argparse
from pathlib import Path

from src.data.tiles import prepare_tiles


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chip aligned imagery and masks into GeoTIFF tiles."
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tile-size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=128)
    parser.add_argument(
        "--drop-empty",
        action="store_true",
        help="Skip tiles with zero positive mask pixels.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.image.exists():
        raise FileNotFoundError(f"image raster does not exist: {args.image}")
    if not args.mask.exists():
        raise FileNotFoundError(f"mask raster does not exist: {args.mask}")

    records = prepare_tiles(
        image_path=args.image,
        mask_path=args.mask,
        output_dir=args.output,
        tile_size=args.tile_size,
        overlap=args.overlap,
        include_empty=not args.drop_empty,
    )
    print(f"Wrote {len(records)} tiles to {args.output}")


if __name__ == "__main__":
    main()
