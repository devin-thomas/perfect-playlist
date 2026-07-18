from collections.abc import Sequence
from typing import Any

import pytest
from spotipy.exceptions import SpotifyException

from perfect_playlist.errors import TrackLookupError
from perfect_playlist.search import get_tracks, inspect_track, search_tracks

TRACK_URI = "spotify:track:354WZaV3u6cuzTG2PmpYwm"
TRACK = {
    "uri": TRACK_URI,
    "external_urls": {"spotify": "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm"},
    "name": "Get The Message",
    "artists": [{"name": "The Paradox"}],
    "album": {"name": "Get The Message"},
    "duration_ms": 162000,
    "explicit": True,
}


class SearchClient:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, object]] = []
        self.track_calls: list[dict[str, object]] = []

    def search(
        self,
        q: str,
        type: str,
        limit: int,
        market: str | None = None,
    ) -> dict[str, Any]:
        self.search_calls.append({"q": q, "type": type, "limit": limit, "market": market})
        return {"tracks": {"items": [TRACK]}}

    def tracks(self, tracks: Sequence[str], market: str | None = None) -> dict[str, Any]:
        self.track_calls.append({"tracks": list(tracks), "market": market})
        return {"tracks": [TRACK]}


class FailingSearchClient(SearchClient):
    def search(
        self,
        q: str,
        type: str,
        limit: int,
        market: str | None = None,
    ) -> dict[str, Any]:
        raise SpotifyException(500, -1, "server error")

    def tracks(self, tracks: Sequence[str], market: str | None = None) -> dict[str, Any]:
        raise SpotifyException(500, -1, "server error")


def test_search_tracks_returns_copyable_uris() -> None:
    client = SearchClient()

    results = search_tracks('track:"Get The Message"', limit=5, client=client)

    assert client.search_calls == [
        {"q": 'track:"Get The Message"', "type": "track", "limit": 5, "market": None},
    ]
    assert results[0].title == "Get The Message"
    assert results[0].artists == ["The Paradox"]
    assert results[0].uri == "spotify:track:354WZaV3u6cuzTG2PmpYwm"
    assert results[0].explicit is True


def test_get_tracks_normalizes_inputs() -> None:
    client = SearchClient()

    results = get_tracks(
        ["https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm?si=abc123"],
        client=client,
    )

    assert client.track_calls == [{"tracks": ["354WZaV3u6cuzTG2PmpYwm"], "market": None}]
    assert results[0].url == "https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm"


def test_search_tracks_maps_spotify_failure() -> None:
    with pytest.raises(TrackLookupError, match="Spotify track search failed"):
        search_tracks('track:"Get The Message"', client=FailingSearchClient())


def test_get_tracks_maps_spotify_failure() -> None:
    with pytest.raises(TrackLookupError, match="metadata lookup failed"):
        get_tracks(["spotify:track:354WZaV3u6cuzTG2PmpYwm"], client=FailingSearchClient())


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("", 4, "must not be empty"),
        ("query", 0, "between 1 and 10"),
        ("query", 11, "between 1 and 10"),
    ],
)
def test_search_tracks_enforces_library_domain_rules(
    query: str, limit: int, message: str
) -> None:
    with pytest.raises(TrackLookupError, match=message):
        search_tracks(query, limit=limit, client=SearchClient())


def test_inspect_track_returns_exactly_one_track() -> None:
    result = inspect_track(TRACK_URI, client=SearchClient())

    assert result.uri == TRACK_URI


def test_track_lookup_rejects_malformed_spotify_metadata() -> None:
    class MalformedMetadataClient(SearchClient):
        def tracks(
            self, tracks: Sequence[str], market: str | None = None
        ) -> dict[str, Any]:
            return {"tracks": [{"uri": TRACK_URI}]}

    with pytest.raises(TrackLookupError, match="invalid track metadata"):
        inspect_track(TRACK_URI, client=MalformedMetadataClient())
