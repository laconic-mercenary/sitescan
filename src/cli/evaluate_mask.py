from __future__ import annotations

import argparse
import json
from pathlib import Path

import rasterio

from src.evaluation.metrics import threshold_sweep


def parse_thresholds(raw_thresholds: str) -> list[float]:
    thresholds = [float(value.strip()) for value in raw_thresholds.split(",") if value.strip()]
    if not thresholds:
        raise argparse.ArgumentTypeError("at least one threshold is required")
    for threshold in thresholds:
        if threshold < 0 or threshold > 1:
            raise argparse.ArgumentTypeError("thresholds must be between 0 and 1")
    return thresholds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate a probability GeoTIFF against a mask.")
    parser.add_argument("--prediction", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--thresholds",
        type=parse_thresholds,
        default=parse_thresholds("0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9"),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.prediction.exists():
        raise FileNotFoundError(f"prediction raster does not exist: {args.prediction}")
    if not args.mask.exists():
        raise FileNotFoundError(f"mask raster does not exist: {args.mask}")

    with rasterio.open(args.prediction) as prediction_ds, rasterio.open(args.mask) as mask_ds:
        if prediction_ds.width != mask_ds.width or prediction_ds.height != mask_ds.height:
            raise ValueError("prediction and mask dimensions do not match")
        if prediction_ds.crs != mask_ds.crs:
            raise ValueError("prediction and mask CRS do not match")
        if prediction_ds.transform != mask_ds.transform:
            raise ValueError("prediction and mask transforms do not match")
        probabilities = prediction_ds.read(1)
        mask = mask_ds.read(1)

    metrics = threshold_sweep(probabilities, mask, args.thresholds)
    output = {
        "prediction": str(args.prediction),
        "mask": str(args.mask),
        "metrics": [metric.to_dict() for metric in metrics],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote evaluation metrics to {args.output}")


if __name__ == "__main__":
    main()
