from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sitescan-matplotlib")

import numpy as np
import rasterio
import torch
from rasterio.windows import Window

from src.config.load import load_model_config, load_train_config
from src.data.tiles import generate_windows
from src.models.build import build_model
from src.training.module import SegmentationModule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run sliding-window sitescan inference.")
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/train.yaml"))
    parser.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    parser.add_argument("--tile-size", type=int, default=None)
    parser.add_argument("--overlap", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    return parser


def load_checkpoint_model(checkpoint_path: Path, model_config_path: Path, train_config_path: Path):
    model_config = load_model_config(model_config_path)
    train_config = load_train_config(train_config_path)
    model = build_model(model_config)
    module = SegmentationModule.load_from_checkpoint(
        checkpoint_path,
        model=model,
        training_config=train_config.training,
        loss_config=train_config.loss,
    )
    module.eval()
    return module


def main() -> None:
    args = build_parser().parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"input raster does not exist: {args.input}")
    if not args.checkpoint.exists():
        raise FileNotFoundError(f"checkpoint does not exist: {args.checkpoint}")

    train_config = load_train_config(args.config)
    tile_size = args.tile_size or train_config.data.tile_size
    overlap = args.overlap or train_config.data.overlap
    device = torch.device(args.device)
    module = load_checkpoint_model(args.checkpoint, args.model_config, args.config).to(device)

    with rasterio.open(args.input) as source:
        windows = generate_windows(source.width, source.height, tile_size, overlap)
        probability_sum = np.zeros((source.height, source.width), dtype="float32")
        weight_sum = np.zeros((source.height, source.width), dtype="float32")

        with torch.no_grad():
            for tile_window in windows:
                raster_window = Window(
                    tile_window.col_off,
                    tile_window.row_off,
                    tile_window.width,
                    tile_window.height,
                )
                tile = source.read(window=raster_window).astype("float32")
                tile = np.nan_to_num(tile, nan=0.0, posinf=0.0, neginf=0.0)
                batch = torch.from_numpy(tile).unsqueeze(0).to(device)
                logits = module(batch)
                probability = torch.sigmoid(logits).squeeze().cpu().numpy().astype("float32")
                row_slice = slice(tile_window.row_off, tile_window.row_off + tile_window.height)
                col_slice = slice(tile_window.col_off, tile_window.col_off + tile_window.width)
                probability_sum[row_slice, col_slice] += probability
                weight_sum[row_slice, col_slice] += 1.0

        probabilities = np.divide(
            probability_sum,
            weight_sum,
            out=np.zeros_like(probability_sum),
            where=weight_sum > 0,
        )
        profile = source.profile.copy()

    profile.update(count=1, dtype="float32", nodata=None, compress="deflate")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(args.output, "w", **profile) as output:
        output.write(probabilities, 1)
    print(f"Wrote probability map to {args.output}")


if __name__ == "__main__":
    main()
