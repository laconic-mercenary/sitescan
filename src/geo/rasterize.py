from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import rasterio
from rasterio.features import rasterize
from rasterio.warp import transform_geom
from shapely.geometry import shape

DEFAULT_LABEL_BUFFER_METERS = 18.0


def load_geojson_features(vector_path: Path) -> list[dict[str, Any]]:
    data = json.loads(vector_path.read_text(encoding="utf-8"))
    if data.get("type") != "FeatureCollection":
        raise ValueError("vector file must be a GeoJSON FeatureCollection")
    return data.get("features", [])


def buffered_shapes_for_reference(
    features: list[dict[str, Any]],
    dst_crs: rasterio.crs.CRS,
    buffer_meters: float,
) -> list[tuple[Any, int]]:
    shapes: list[tuple[Any, int]] = []
    for feature in features:
        geometry = feature.get("geometry")
        if not geometry:
            continue
        projected = transform_geom("EPSG:4326", dst_crs, geometry)
        geom = shape(projected)
        if geom.is_empty:
            continue
        if geom.geom_type in {"Point", "LineString", "MultiLineString"}:
            geom = geom.buffer(buffer_meters)
        shapes.append((geom, 1))
    return shapes


def rasterize_labels(
    vector_path: Path,
    reference_path: Path,
    output_path: Path,
    buffer_meters: float = DEFAULT_LABEL_BUFFER_METERS,
) -> int:
    features = load_geojson_features(vector_path)
    if not features:
        raise ValueError(f"no GeoJSON features found in {vector_path}")

    with rasterio.open(reference_path) as reference:
        shapes = buffered_shapes_for_reference(features, reference.crs, buffer_meters)
        if not shapes:
            raise ValueError("no usable vector geometries found")
        mask = rasterize(
            shapes,
            out_shape=(reference.height, reference.width),
            transform=reference.transform,
            fill=0,
            dtype="uint8",
            all_touched=True,
        )
        profile = reference.profile.copy()

    profile.update(
        count=1,
        dtype="uint8",
        nodata=0,
        compress="deflate",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **profile) as output:
        output.write(mask, 1)
    return int(mask.sum())
