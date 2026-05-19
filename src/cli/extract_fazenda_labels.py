from __future__ import annotations

import argparse
from pathlib import Path

from src.geo.kml import FAZENDA_COLORADA_BBOX, extract_features_to_geojson


def parse_bbox(raw_bbox: str) -> tuple[float, float, float, float]:
    parts = [float(part.strip()) for part in raw_bbox.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("bbox must be min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = parts
    if min_lon >= max_lon or min_lat >= max_lat:
        raise argparse.ArgumentTypeError("bbox min values must be less than max values")
    return min_lon, min_lat, max_lon, max_lat


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract Fazenda Colorada candidate label vectors from Amazon Geoglyphs KML."
    )
    parser.add_argument(
        "--kml",
        type=Path,
        default=Path("data/external/amazon_geoglyphs/live/amazon_geoglyphs.kml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/fazenda_colorada/fazenda_colorada_vectors.geojson"),
    )
    parser.add_argument(
        "--bbox",
        type=parse_bbox,
        default=FAZENDA_COLORADA_BBOX,
        help="min_lon,min_lat,max_lon,max_lat in EPSG:4326",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.kml.exists():
        raise FileNotFoundError(f"KML file does not exist: {args.kml}")

    feature_count = extract_features_to_geojson(args.kml, args.output, args.bbox)
    print(f"Wrote {feature_count} candidate label features to {args.output}")


if __name__ == "__main__":
    main()
