from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
import torch
from torch.utils.data import Dataset


class TileSegmentationDataset(Dataset):
    def __init__(self, image_paths: list[Path], mask_paths: list[Path]) -> None:
        if len(image_paths) != len(mask_paths):
            raise ValueError("image_paths and mask_paths must have the same length")
        if not image_paths:
            raise ValueError("dataset cannot be empty")
        self.image_paths = image_paths
        self.mask_paths = mask_paths

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        with rasterio.open(self.image_paths[index]) as image:
            image_array = image.read().astype("float32")
        image_array = np.nan_to_num(image_array, nan=0.0, posinf=0.0, neginf=0.0)
        with rasterio.open(self.mask_paths[index]) as mask:
            mask_array = mask.read(1).astype("float32")
        mask_array = (mask_array > 0).astype("float32")
        mask_array = np.expand_dims(mask_array, axis=0)
        return torch.from_numpy(image_array), torch.from_numpy(mask_array)


def find_tile_pairs(tile_dir: Path) -> tuple[list[Path], list[Path]]:
    image_dir = tile_dir / "images"
    mask_dir = tile_dir / "masks"
    if not image_dir.exists():
        raise FileNotFoundError(f"tile image directory does not exist: {image_dir}")
    if not mask_dir.exists():
        raise FileNotFoundError(f"tile mask directory does not exist: {mask_dir}")

    image_paths = sorted(image_dir.glob("*.tif"))
    mask_paths = [mask_dir / image_path.name for image_path in image_paths]
    missing_masks = [path for path in mask_paths if not path.exists()]
    if missing_masks:
        raise FileNotFoundError(f"missing mask for tile: {missing_masks[0]}")
    return image_paths, mask_paths


def split_tile_pairs(
    image_paths: list[Path],
    mask_paths: list[Path],
    val_split: float,
    test_split: float,
    seed: int,
) -> dict[str, tuple[list[Path], list[Path]]]:
    rng = np.random.default_rng(seed)
    indices = np.arange(len(image_paths))
    rng.shuffle(indices)

    test_count = int(len(indices) * test_split)
    val_count = int(len(indices) * val_split)
    test_indices = indices[:test_count]
    val_indices = indices[test_count : test_count + val_count]
    train_indices = indices[test_count + val_count :]

    def select(selected: np.ndarray) -> tuple[list[Path], list[Path]]:
        return [image_paths[i] for i in selected], [mask_paths[i] for i in selected]

    return {
        "train": select(train_indices),
        "val": select(val_indices),
        "test": select(test_indices),
    }
