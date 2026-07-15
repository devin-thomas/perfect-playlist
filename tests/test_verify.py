from perfect_playlist.models import TrackSequence
from perfect_playlist.verify import compare_track_sequences


def _sequence(*indices: int) -> TrackSequence:
    return TrackSequence(uris=tuple(f"spotify:track:{index:022d}" for index in indices))


def test_compare_track_sequences_preserves_first_difference_only() -> None:
    result = compare_track_sequences(_sequence(1, 2, 3), _sequence(1, 4, 3))

    assert result.matches is False
    assert result.left_count == result.right_count == 3
    assert result.first_difference_position == 2
    assert result.left_uri == "spotify:track:0000000000000000000002"
    assert result.right_uri == "spotify:track:0000000000000000000004"


def test_compare_track_sequences_count_mismatch_has_no_content_diagnostics() -> None:
    result = compare_track_sequences(_sequence(1), _sequence())

    assert result.matches is False
    assert result.left_count == 1
    assert result.right_count == 0
    assert result.first_difference_position is None
    assert result.left_uri is None
    assert result.right_uri is None
