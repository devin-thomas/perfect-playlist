from collections.abc import Sequence
from typing import Any

import pytest

from spotify_exact.errors import InvalidTrackRefError
from spotify_exact.playlist import add_items_in_order, create_playlist_from_uris


def _track_uri(index: int) -> str:
    return f"spotify:track:{index:022d}"


class PlaylistClient:
    def __init__(self, playlist_items: list[str] | None = None) -> None:
        self.created: list[dict[str, object]] = []
        self.added: list[dict[str, object]] = []
        self._playlist_items = playlist_items or []

    def current_user(self) -> dict[str, object]:
        return {"id": "user-123"}

    def user_playlist_create(
        self,
        user: str,
        name: str,
        public: bool,
        description: str,
        collaborative: bool = False,
    ) -> dict[str, object]:
        self.created.append(
            {
                "user": user,
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

    def playlist_add_items(
        self,
        playlist_id: str,
        items: Sequence[str],
        position: int | None = None,
    ) -> dict[str, Any]:
        kwargs = {"position": position}
        self.added.append({"playlist_id": playlist_id, "items": list(items), "kwargs": kwargs})
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


def test_create_playlist_validates_before_write() -> None:
    client = PlaylistClient()

    with pytest.raises(InvalidTrackRefError):
        create_playlist_from_uris("Bad", ["not a track"], client=client)

    assert client.created == []
    assert client.added == []


def test_create_playlist_adds_and_verifies_exact_order() -> None:
    uris = [_track_uri(index) for index in range(3)]
    client = PlaylistClient(playlist_items=uris)

    result = create_playlist_from_uris("Exact", uris, public=False, verify=True, client=client)

    assert result.playlist.id == "playlist-123"
    assert result.playlist.snapshot_id == "snapshot-1"
    assert result.added_uris == uris
    assert result.verified is True
    assert client.created[0]["public"] is False
    assert client.added == [
        {"playlist_id": "playlist-123", "items": uris, "kwargs": {"position": None}},
    ]


def test_add_items_in_order_chunks_sequentially_and_positions_first_chunk_only() -> None:
    uris = [_track_uri(index) for index in range(101)]
    client = PlaylistClient()

    snapshot_id = add_items_in_order("playlist-123", uris, start_position=5, client=client)

    assert snapshot_id == "snapshot-2"
    assert client.added[0] == {
        "playlist_id": "playlist-123",
        "items": uris[:100],
        "kwargs": {"position": 5},
    }
    assert client.added[1] == {
        "playlist_id": "playlist-123",
        "items": uris[100:],
        "kwargs": {"position": None},
    }
