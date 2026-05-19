from pathlib import Path

from src.geo.kml import (
    KmlFeature,
    feature_intersects_bbox,
    parse_coordinate_text,
    parse_kml_features,
)


def test_parse_coordinate_text_ignores_altitude() -> None:
    coords = parse_coordinate_text("-67.1,-9.1,0 -67.2,-9.2,123")

    assert coords == [(-67.1, -9.1), (-67.2, -9.2)]


def test_parse_kml_features_reads_points_and_lines(tmp_path: Path) -> None:
    kml = tmp_path / "sample.kml"
    kml.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <name>line</name>
      <LineString><coordinates>-67.1,-9.1,0 -67.2,-9.2,0</coordinates></LineString>
    </Placemark>
    <Placemark>
      <name>point</name>
      <Point><coordinates>-67.3,-9.3,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>
""",
        encoding="utf-8",
    )

    features = parse_kml_features(kml)

    assert [feature.name for feature in features] == ["line", "point"]
    assert [feature.geometry_type for feature in features] == ["LineString", "Point"]


def test_feature_intersects_bbox() -> None:
    feature = KmlFeature(
        name="outside",
        geometry_type="Point",
        coordinates=[(-67.5, -9.8)],
    )

    assert not feature_intersects_bbox(feature, (0, 0, 1, 1))
