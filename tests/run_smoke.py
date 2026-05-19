from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.test_kml import (
    test_feature_intersects_bbox,
    test_parse_coordinate_text_ignores_altitude,
    test_parse_kml_features_reads_points_and_lines,
)
from tests.test_metrics import test_compute_binary_metrics
from tests.test_tiles import (
    test_generate_windows_covers_edges,
    test_generate_windows_rejects_invalid_overlap,
    test_generate_windows_uses_overlap_stride,
)


def main() -> None:
    test_parse_coordinate_text_ignores_altitude()
    test_feature_intersects_bbox()
    test_generate_windows_uses_overlap_stride()
    test_generate_windows_covers_edges()
    test_generate_windows_rejects_invalid_overlap()
    test_compute_binary_metrics()

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        test_parse_kml_features_reads_points_and_lines(Path(tmp))
    print("smoke tests passed")


if __name__ == "__main__":
    main()
