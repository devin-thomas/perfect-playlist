from typing import Any

import pytest

from perfect_playlist.errors import SourceAccessError, SourceMalformedError, SourceSpotifyError
from perfect_playlist.io import read_source
from perfect_playlist.track_refs import normalize_playlist_ref

TRACK_A = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK_B = "spotify:track:78APbsosmvDYIwZHjzC5ZE"
PLAYLIST_ID = "37i9dQZF1DXcBWIGoYBM5M"


class SpotifySourceClient:
    def __init__(self, pages: list[dict[str, Any]]) -> None:
        self.pages = pages
        self.track_ids: list[str] = []
        self.playlist_calls: list[tuple[int, int]] = []

    def track(self, track_id: str, market: str | None = None) -> dict[str, Any]:
        self.track_ids.append(track_id)
        return {"uri": TRACK_A}

    def playlist_items(
        self, playlist_id: str, fields: str, limit: int, offset: int
    ) -> dict[str, Any]:
        self.playlist_calls.append((limit, offset))
        return self.pages[len(self.playlist_calls) - 1]


def test_normalize_playlist_reference_accepts_uri_and_link() -> None:
    assert normalize_playlist_ref(f"spotify:playlist:{PLAYLIST_ID}") == (
        f"spotify:playlist:{PLAYLIST_ID}"
    )
    assert normalize_playlist_ref(f"https://open.spotify.com/playlist/{PLAYLIST_ID}?si=test") == (
        f"spotify:playlist:{PLAYLIST_ID}"
    )


def test_read_source_resolves_single_track_reference() -> None:
    client = SpotifySourceClient([])

    result = read_source(
        "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm?si=test", client=client
    )

    assert result.uris == (TRACK_A,)
    assert client.track_ids == ["354WZaV3u6cuzTG2PmpYwm"]


def test_read_source_resolves_all_playlist_pages_in_order() -> None:
    client = SpotifySourceClient(
        [
            {
                "items": [{"track": {"uri": TRACK_A}}, {"track": {"uri": TRACK_B}}],
                "next": "next-page",
            },
            {"items": [{"track": {"uri": TRACK_A}}], "next": None},
        ]
    )

    result = read_source(f"spotify:playlist:{PLAYLIST_ID}", client=client)

    assert result.uris == (TRACK_A, TRACK_B, TRACK_A)
    assert client.playlist_calls == [(100, 0), (100, 2)]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("354WZaV3u6cuzTG2PmpYwm", "Raw Spotify track ids"),
        ("-", "Stdin"),
        ("https://example.com/tracks.yaml", "download the document locally"),
        ("spotify:album:354WZaV3u6cuzTG2PmpYwm", "Expected a Spotify playlist URI or URL"),
    ],
)
def test_read_source_rejects_unsupported_remote_and_untyped_inputs(
    value: str, message: str
) -> None:
    with pytest.raises(SourceMalformedError, match=message):
        read_source(value)


def test_read_source_rejects_playlist_items_without_track_uri() -> None:
    client = SpotifySourceClient([{"items": [{"track": None}], "next": None}])

    with pytest.raises(SourceAccessError, match="inaccessible track"):
        read_source(f"spotify:playlist:{PLAYLIST_ID}", client=client)


def test_read_source_maps_malformed_spotify_track_uri_to_source_error() -> None:
    class MalformedTrackClient(SpotifySourceClient):
        def track(self, track_id: str, market: str | None = None) -> dict[str, Any]:
            return {"uri": "not-a-track"}

    with pytest.raises(SourceSpotifyError, match="invalid track URI"):
        read_source(f"spotify:track:{TRACK_A.rsplit(':', 1)[1]}", client=MalformedTrackClient([]))


def test_read_source_maps_malformed_spotify_playlist_uri_to_source_error() -> None:
    client = SpotifySourceClient(
        [{"items": [{"track": {"uri": "not-a-track"}}], "next": None}]
    )

    with pytest.raises(SourceSpotifyError, match="invalid track URI"):
        read_source(f"spotify:playlist:{PLAYLIST_ID}", client=client)


def test_read_source_rejects_malformed_spotify_page_shape() -> None:
    client = SpotifySourceClient([{"items": "not-a-list", "next": None}])

    with pytest.raises(SourceSpotifyError, match="invalid items"):
        read_source(f"spotify:playlist:{PLAYLIST_ID}", client=client)
