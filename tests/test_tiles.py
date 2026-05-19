from src.data.tiles import generate_windows


def test_generate_windows_uses_overlap_stride() -> None:
    windows = generate_windows(width=1024, height=1024, tile_size=512, overlap=256)

    assert len(windows) == 9
    assert int(windows[-1].col_off) == 512
    assert int(windows[-1].row_off) == 512


def test_generate_windows_covers_edges() -> None:
    windows = generate_windows(width=1100, height=900, tile_size=512, overlap=128)

    assert windows[-1].col_off == 588
    assert windows[-1].row_off == 388


def test_generate_windows_rejects_invalid_overlap() -> None:
    try:
        generate_windows(width=1024, height=1024, tile_size=512, overlap=512)
    except ValueError as err:
        assert "overlap" in str(err)
    else:
        raise AssertionError("expected ValueError")
