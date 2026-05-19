from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TileRecord:
    index: int
    image: str
    mask: str
    col_off: int
    row_off: int
    width: int
    height: int
    positive_pixels: int


@dataclass(frozen=True)
class TileWindow:
    col_off: int
    row_off: int
    width: int
    height: int


def generate_windows(width: int, height: int, tile_size: int, overlap: int) -> list[TileWindow]:
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must be >= 0 and less than tile_size")
    if width < tile_size or height < tile_size:
        raise ValueError("raster dimensions must be at least tile_size")
    stride = tile_size - overlap
    col_offsets = list(range(0, width - tile_size + 1, stride))
    row_offsets = list(range(0, height - tile_size + 1, stride))
    if col_offsets[-1] != width - tile_size:
        col_offsets.append(width - tile_size)
    if row_offsets[-1] != height - tile_size:
        row_offsets.append(height - tile_size)

    windows: list[TileWindow] = []
    for row_off in row_offsets:
        for col_off in col_offsets:
            windows.append(TileWindow(col_off, row_off, tile_size, tile_size))
    return windows


def validate_alignment(image, mask) -> None:
    if image.width != mask.width or image.height != mask.height:
        raise ValueError("image and mask dimensions do not match")
    if image.crs != mask.crs:
        raise ValueError("image and mask CRS do not match")
    if image.transform != mask.transform:
        raise ValueError("image and mask transforms do not match")


def prepare_tiles(
    image_path: Path,
    mask_path: Path,
    output_dir: Path,
    tile_size: int,
    overlap: int,
    include_empty: bool = True,
) -> list[TileRecord]:
    import numpy as np
    import rasterio
    from rasterio.windows import Window

    output_image_dir = output_dir / "images"
    output_mask_dir = output_dir / "masks"
    output_image_dir.mkdir(parents=True, exist_ok=True)
    output_mask_dir.mkdir(parents=True, exist_ok=True)

    records: list[TileRecord] = []
    with rasterio.open(image_path) as image, rasterio.open(mask_path) as mask:
        validate_alignment(image, mask)
        tile_windows = generate_windows(image.width, image.height, tile_size, overlap)
        for tile_window in tile_windows:
            raster_window = Window(
                tile_window.col_off,
                tile_window.row_off,
                tile_window.width,
                tile_window.height,
            )
            mask_data = mask.read(1, window=raster_window)
            positive_pixels = int(np.count_nonzero(mask_data))
            if positive_pixels == 0 and not include_empty:
                continue

            index = len(records)
            image_tile = image.read(window=raster_window)
            image_profile = image.profile.copy()
            image_profile.update(
                height=tile_size,
                width=tile_size,
                transform=image.window_transform(raster_window),
                compress="deflate",
            )
            mask_profile = mask.profile.copy()
            mask_profile.update(
                height=tile_size,
                width=tile_size,
                transform=mask.window_transform(raster_window),
                compress="deflate",
            )

            image_output = output_image_dir / f"tile_{index:05d}.tif"
            mask_output = output_mask_dir / f"tile_{index:05d}.tif"
            with rasterio.open(image_output, "w", **image_profile) as dst_image:
                dst_image.write(image_tile)
            with rasterio.open(mask_output, "w", **mask_profile) as dst_mask:
                dst_mask.write(mask_data, 1)

            records.append(
                TileRecord(
                    index=index,
                    image=str(image_output),
                    mask=str(mask_output),
                    col_off=tile_window.col_off,
                    row_off=tile_window.row_off,
                    width=tile_window.width,
                    height=tile_window.height,
                    positive_pixels=positive_pixels,
                )
            )

    manifest_path = output_dir / "manifest.json"
    manifest = {
        "image": str(image_path),
        "mask": str(mask_path),
        "tile_size": tile_size,
        "overlap": overlap,
        "tile_count": len(records),
        "tiles": [asdict(record) for record in records],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return records
