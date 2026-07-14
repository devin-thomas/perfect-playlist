from collections.abc import Sequence
from typing import Any

import pytest
from spotipy.exceptions import SpotifyException

from perfect_playlist.errors import InvalidTrackRefError, PlaylistAddError, PlaylistCreateError
from perfect_playlist.playlist import add_items_in_order, create_playlist_from_uris


def _track_uri(index: int) -> str:
    return f"spotify:track:{index:022d}"


class PlaylistClient:
    def __init__(
        self,
        playlist_items: list[str] | None = None,
        persisted_public: bool | None = None,
    ) -> None:
        self.created: list[dict[str, object]] = []
        self.added: list[dict[str, object]] = []
        self._playlist_items = playlist_items or []
        self._persisted_public = persisted_public

    def current_user_playlist_create(
        self,
        name: str,
        public: bool,
        collaborative: bool = False,
        description: str = "",
    ) -> dict[str, object]:
        self.created.append(
            {
                "name": name,
                "public": public,
                "description": description,
                "collaborative": collaborative,
            }
        )
        return {
            "id": "playlist-123",
            "uri": "spotify:playlist:playlist-123",
            "external_urls": {"spotify": "https://open.spotify.com/playlist/playlist-123"},
            "name": name,
        }

    def playlist(self, playlist_id: str, fields: str) -> dict[str, object]:
        requested_public = self.created[-1]["public"]
        return {
            "id": playlist_id,
            "public": (
                requested_public if self._persisted_public is None else self._persisted_public
            ),
        }

    def playlist_add_items(
        self,
        playlist_id: str,
        items: Sequence[str],
    ) -> dict[str, Any]:
        self.added.append({"playlist_id": playlist_id, "items": list(items)})
        return {"snapshot_id": f"snapshot-{len(self.added)}"}

    def playlist_items(
        self,
        playlist_id: str,
        fields: str,
        limit: int,
        offset: int,
    ) -> dict[str, object]:
        page = self._playlist_items[offset : offset + limit]
        return {
            "items": [{"track": {"uri": uri}} for uri in page],
            "next": None,
        }


class FailingCreateClient(PlaylistClient):
    def current_user_playlist_create(
        self,
        name: str,
        public: bool,
        collaborative: bool = False,
        description: str = "",
    ) -> dict[str, object]:
        raise SpotifyException(401, -1, "unauthorized")


class FailingAddClient(PlaylistClient):
    def playlist_add_items(
        self,
        playlist_id: str,
        items: Sequence[str],
    ) -> dict[str, Any]:
        raise SpotifyException(500, -1, "server error")


def test_create_playlist_validates_before_write() -> None:
    client = PlaylistClient()

    with pytest.raises(InvalidTrackRefError):
        create_playlist_from_uris("Bad", ["not a track"], client=client)

    assert client.created == []
    assert client.added == []


def test_create_playlist_adds_in_exact_order() -> None:
    uris = [_track_uri(index) for index in range(3)]
    client = PlaylistClient(playlist_items=uris)

    result = create_playlist_from_uris("Exact", uris, public=False, client=client)

    assert result.playlist.id == "playlist-123"
    assert result.playlist.snapshot_id == "snapshot-1"
    assert result.added_uris == uris
    assert client.created[0]["public"] is False
    assert client.added == [
        {"playlist_id": "playlist-123", "items": uris},
    ]


def test_private_playlist_aborts_before_adding_when_spotify_persists_it_as_public() -> None:
    client = PlaylistClient(persisted_public=True)

    with pytest.raises(PlaylistCreateError, match="stored playlist as public"):
        create_playlist_from_uris(
            "Must stay private",
            [_track_uri(1)],
            public=False,
            client=client,
        )

    assert client.added == []


def test_add_items_in_order_chunks_sequentially() -> None:
    uris = [_track_uri(index) for index in range(101)]
    client = PlaylistClient()

    snapshot_id = add_items_in_order("playlist-123", uris, client=client)

    assert snapshot_id == "snapshot-2"
    assert client.added[0] == {
        "playlist_id": "playlist-123",
        "items": uris[:100],
    }
    assert client.added[1] == {
        "playlist_id": "playlist-123",
        "items": uris[100:],
    }


def test_create_playlist_maps_spotify_create_failure() -> None:
    with pytest.raises(PlaylistCreateError, match="Spotify rejected playlist creation"):
        create_playlist_from_uris("Exact", [_track_uri(1)], client=FailingCreateClient())


def test_add_items_reports_chunk_and_partial_playlist_url() -> None:
    with pytest.raises(PlaylistAddError) as exc_info:
        add_items_in_order(
            "playlist-123",
            [_track_uri(1)],
            playlist_url="https://open.spotify.com/playlist/playlist-123",
            client=FailingAddClient(),
        )

    message = str(exc_info.value)
    assert "chunk 1" in message
    assert "https://open.spotify.com/playlist/playlist-123" in message
