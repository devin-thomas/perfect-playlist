from spotify_exact.playlist import chunked


def test_chunked_splits_spotify_batch_size() -> None:
    items = list(range(101))

    assert list(chunked(items, 100)) == [list(range(100)), [100]]


def test_chunked_rejects_zero_size() -> None:
    try:
        list(chunked([1], 0))
    except ValueError as exc:
        assert "at least 1" in str(exc)
    else:
        raise AssertionError("Expected ValueError")

