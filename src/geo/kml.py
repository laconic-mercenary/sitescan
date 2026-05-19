from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}
FAZENDA_COLORADA_BBOX = (-67.5375, -9.8810, -67.5320, -9.8710)


@dataclass(frozen=True)
class KmlFeature:
    name: str
    geometry_type: str
    coordinates: list[tuple[float, float]]
    description: str | None = None


def parse_coordinate_text(text: str | None) -> list[tuple[float, float]]:
    if not text:
        return []
    coordinates: list[tuple[float, float]] = []
    for raw_coord in text.split():
        parts = raw_coord.split(",")
        if len(parts) < 2:
            continue
        coordinates.append((float(parts[0]), float(parts[1])))
    return coordinates


def strip_description(raw_description: str | None) -> str | None:
    if raw_description is None:
        return None
    without_tags = re.sub(r"<[^>]+>", " ", raw_description)
    normalized = re.sub(r"\s+", " ", without_tags).strip()
    return normalized or None


def parse_kml_features(kml_path: Path) -> list[KmlFeature]:
    root = ET.parse(kml_path).getroot()
    features: list[KmlFeature] = []

    for placemark in root.findall(".//kml:Placemark", KML_NS):
        name = placemark.findtext("kml:name", default="", namespaces=KML_NS).strip()
        description = strip_description(
            placemark.findtext("kml:description", default=None, namespaces=KML_NS)
        )

        for line_string in placemark.findall(".//kml:LineString", KML_NS):
            coords_text = line_string.findtext("kml:coordinates", default="", namespaces=KML_NS)
            coordinates = parse_coordinate_text(coords_text)
            if coordinates:
                features.append(KmlFeature(name, "LineString", coordinates, description))

        for point in placemark.findall(".//kml:Point", KML_NS):
            coords_text = point.findtext("kml:coordinates", default="", namespaces=KML_NS)
            coordinates = parse_coordinate_text(coords_text)
            if coordinates:
                features.append(KmlFeature(name, "Point", coordinates[:1], description))


    return features


def feature_intersects_bbox(feature: KmlFeature, bbox: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bbox
    return any(
        min_lon <= lon <= max_lon and min_lat <= lat <= max_lat
        for lon, lat in feature.coordinates
    )


def kml_feature_to_geojson_feature(feature: KmlFeature) -> dict[str, Any]:
    if feature.geometry_type == "Point":
        geometry: dict[str, Any] = {
            "type": "Point",
            "coordinates": list(feature.coordinates[0]),
        }
    elif feature.geometry_type == "LineString":
        geometry = {
            "type": "LineString",
            "coordinates": [list(coord) for coord in feature.coordinates],
        }
    else:
        raise ValueError(f"unsupported KML feature type: {feature.geometry_type}")

    return {
        "type": "Feature",
        "properties": {
            "name": feature.name,
            "description": feature.description,
            "source_geometry_type": feature.geometry_type,
        },
        "geometry": geometry,
    }


def extract_features_to_geojson(
    kml_path: Path,
    output_path: Path,
    bbox: tuple[float, float, float, float] = FAZENDA_COLORADA_BBOX,
) -> int:
    features = [
        kml_feature_to_geojson_feature(feature)
        for feature in parse_kml_features(kml_path)
        if feature_intersects_bbox(feature, bbox)
    ]
    collection = {
        "type": "FeatureCollection",
        "name": "fazenda_colorada_candidate_labels",
        "crs": {
            "type": "name",
            "properties": {"name": "EPSG:4326"},
        },
        "features": features,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
    return len(features)
