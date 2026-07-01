import pytest

from perfect_playlist.errors import InvalidTrackRefError
from perfect_playlist.track_refs import extract_track_id, is_track_uri, normalize_track_ref

TRACK_ID = "354WZaV3u6cuzTG2PmpYwm"


def test_normalize_track_uri() -> None:
    assert normalize_track_ref(f"spotify:track:{TRACK_ID}") == f"spotify:track:{TRACK_ID}"


def test_normalize_track_url() -> None:
    assert (
        normalize_track_ref(f"https://open.spotify.com/track/{TRACK_ID}?si=abc123")
        == f"spotify:track:{TRACK_ID}"
    )


def test_extract_track_id() -> None:
    assert extract_track_id(f"spotify:track:{TRACK_ID}") == TRACK_ID


def test_is_track_uri() -> None:
    assert is_track_uri(f"spotify:track:{TRACK_ID}") is True
    assert is_track_uri(f"https://open.spotify.com/track/{TRACK_ID}") is False


@pytest.mark.parametrize(
    "value",
    [
        "spotify:album:354WZaV3u6cuzTG2PmpYwm",
        "spotify:playlist:354WZaV3u6cuzTG2PmpYwm",
        "https://youtube.com/watch?v=abc",
        "Get The Message by The Paradox",
    ],
)
def test_rejects_non_track_refs(value: str) -> None:
    with pytest.raises(InvalidTrackRefError):
        normalize_track_ref(value)

