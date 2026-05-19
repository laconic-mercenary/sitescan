from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sitescan-matplotlib")

import lightning as L
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from torch.utils.data import DataLoader

from src.config.load import load_model_config, load_train_config
from src.models.build import build_model
from src.training.dataset import TileSegmentationDataset, find_tile_pairs, split_tile_pairs
from src.training.module import SegmentationModule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train a sitescan segmentation model.")
    parser.add_argument("--config", type=Path, default=Path("configs/train.yaml"))
    parser.add_argument("--model-config", type=Path, default=Path("configs/model.yaml"))
    parser.add_argument("--tile-dir", type=Path, default=None)
    parser.add_argument("--max-epochs", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--num-workers", type=int, default=None)
    parser.add_argument("--accelerator", default="auto")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    train_config = load_train_config(args.config)
    model_config = load_model_config(args.model_config)

    tile_dir = args.tile_dir or train_config.data.tile_dir
    image_paths, mask_paths = find_tile_pairs(tile_dir)
    splits = split_tile_pairs(
        image_paths,
        mask_paths,
        train_config.data.val_split,
        train_config.data.test_split,
        train_config.training.seed,
    )
    train_images, train_masks = splits["train"]
    val_images, val_masks = splits["val"]
    if not val_images:
        val_images, val_masks = train_images, train_masks

    L.seed_everything(train_config.training.seed, workers=True)
    model = build_model(model_config)
    module = SegmentationModule(model, train_config.training, train_config.loss)
    batch_size = args.batch_size or train_config.training.batch_size
    max_epochs = args.max_epochs or train_config.training.max_epochs
    num_workers = (
        args.num_workers if args.num_workers is not None else train_config.data.num_workers
    )

    train_loader = DataLoader(
        TileSegmentationDataset(train_images, train_masks),
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
    )
    val_loader = DataLoader(
        TileSegmentationDataset(val_images, val_masks),
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
    )

    checkpoint = ModelCheckpoint(
        dirpath=train_config.checkpoint.dirpath,
        monitor=train_config.checkpoint.monitor,
        mode=train_config.checkpoint.mode,
        save_top_k=train_config.checkpoint.save_top_k,
    )
    early_stop = EarlyStopping(
        monitor=train_config.checkpoint.monitor,
        mode=train_config.checkpoint.mode,
        patience=train_config.training.early_stop_patience,
    )
    trainer = L.Trainer(
        max_epochs=max_epochs,
        accelerator=args.accelerator,
        callbacks=[checkpoint, early_stop],
        log_every_n_steps=1,
    )
    trainer.fit(module, train_loader, val_loader)


if __name__ == "__main__":
    main()
