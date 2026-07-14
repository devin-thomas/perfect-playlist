import pytest
from pydantic import ValidationError

from perfect_playlist import TrackSequence

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"


def test_track_sequence_normalizes_urls_and_preserves_order_and_duplicates() -> None:
    sequence = TrackSequence(
        uris=(
            f" https://open.spotify.com/track/{TRACK_A.rsplit(':', 1)[1]}?si=abc ",
            TRACK_B,
            TRACK_A,
        )
    )

    assert sequence.uris == (TRACK_A, TRACK_B, TRACK_A)
    assert list(sequence.uris) == [TRACK_A, TRACK_B, TRACK_A]
    assert sequence[1] == TRACK_B
    assert len(sequence) == 3


def test_track_sequence_accepts_empty_sequences() -> None:
    assert TrackSequence().uris == ()
    assert TrackSequence(uris=()).uris == ()


@pytest.mark.parametrize(
    "uris",
    [
        [TRACK_A, "not a track"],
        [TRACK_A, 42],
        "spotify:track:354WZaV3u6cuzTG2PmpYwm",
    ],
)
def test_track_sequence_rejects_the_whole_sequence_when_an_entry_is_invalid(
    uris: object,
) -> None:
    with pytest.raises((TypeError, ValidationError)):
        TrackSequence(uris=uris)  # type: ignore[arg-type]


def test_track_sequence_has_no_playlist_metadata() -> None:
    with pytest.raises(ValidationError):
        TrackSequence(uris=(TRACK_A,), name="Playlist")  # type: ignore[call-arg]
