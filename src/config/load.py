from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ModelConfig:
    architecture: str
    encoder: str
    encoder_weights: str | None
    in_channels: int
    num_classes: int
    decoder_channels: tuple[int, ...]
    activation: str | None


@dataclass(frozen=True)
class DataConfig:
    tile_dir: Path
    annotation_dir: Path
    tile_size: int
    overlap: int
    val_split: float
    test_split: float
    num_workers: int


@dataclass(frozen=True)
class TrainingConfig:
    batch_size: int
    max_epochs: int
    learning_rate: float
    weight_decay: float
    early_stop_patience: int
    pos_weight: float
    seed: int


@dataclass(frozen=True)
class LossConfig:
    dice_weight: float
    bce_weight: float


@dataclass(frozen=True)
class OptimizerConfig:
    warmup_epochs: int


@dataclass(frozen=True)
class CheckpointConfig:
    dirpath: Path
    monitor: str
    mode: str
    save_top_k: int


@dataclass(frozen=True)
class TrainConfig:
    data: DataConfig
    training: TrainingConfig
    loss: LossConfig
    optimizer: OptimizerConfig
    checkpoint: CheckpointConfig


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"config file does not exist: {path}")
    with path.open("r", encoding="utf-8") as config_file:
        raw = yaml.safe_load(config_file)
    if not isinstance(raw, dict):
        raise ValueError(f"config file must contain a mapping: {path}")
    return raw


def load_model_config(path: Path) -> ModelConfig:
    raw = read_yaml(path)
    config = ModelConfig(
        architecture=str(raw["architecture"]),
        encoder=str(raw["encoder"]),
        encoder_weights=raw["encoder_weights"],
        in_channels=int(raw["in_channels"]),
        num_classes=int(raw["num_classes"]),
        decoder_channels=tuple(int(value) for value in raw["decoder_channels"]),
        activation=raw["activation"],
    )
    if config.architecture != "unet":
        raise ValueError("only unet architecture is currently supported")
    if config.in_channels <= 0:
        raise ValueError("model in_channels must be positive")
    if config.num_classes != 1:
        raise ValueError("only binary segmentation with num_classes=1 is currently supported")
    return config


def load_train_config(path: Path) -> TrainConfig:
    raw = read_yaml(path)
    data = raw["data"]
    training = raw["training"]
    loss = raw["loss"]
    optimizer = raw["optimizer"]
    checkpoint = raw["checkpoint"]

    config = TrainConfig(
        data=DataConfig(
            tile_dir=Path(data["tile_dir"]),
            annotation_dir=Path(data["annotation_dir"]),
            tile_size=int(data["tile_size"]),
            overlap=int(data["overlap"]),
            val_split=float(data["val_split"]),
            test_split=float(data["test_split"]),
            num_workers=int(data["num_workers"]),
        ),
        training=TrainingConfig(
            batch_size=int(training["batch_size"]),
            max_epochs=int(training["max_epochs"]),
            learning_rate=float(training["learning_rate"]),
            weight_decay=float(training["weight_decay"]),
            early_stop_patience=int(training["early_stop_patience"]),
            pos_weight=float(training["pos_weight"]),
            seed=int(training["seed"]),
        ),
        loss=LossConfig(
            dice_weight=float(loss["dice_weight"]),
            bce_weight=float(loss["bce_weight"]),
        ),
        optimizer=OptimizerConfig(
            warmup_epochs=int(optimizer["warmup_epochs"]),
        ),
        checkpoint=CheckpointConfig(
            dirpath=Path(checkpoint["dirpath"]),
            monitor=str(checkpoint["monitor"]),
            mode=str(checkpoint["mode"]),
            save_top_k=int(checkpoint["save_top_k"]),
        ),
    )
    if config.data.val_split < 0 or config.data.test_split < 0:
        raise ValueError("validation and test splits must be non-negative")
    if config.data.val_split + config.data.test_split >= 1:
        raise ValueError("validation plus test split must be less than 1")
    if config.training.batch_size <= 0:
        raise ValueError("batch_size must be positive")
    return config
