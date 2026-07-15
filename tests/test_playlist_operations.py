from collections.abc import Sequence
from typing import Any

import pytest
from spotipy.exceptions import SpotifyException

from perfect_playlist.errors import (
    InvalidTrackRefError,
    PlaylistAddError,
    PlaylistCreateError,
    PlaylistVerificationError,
)
from perfect_playlist.models import TrackSequence
from perfect_playlist.playlist import (
    add_items_in_order,
    add_to_playlist,
    build_public_playlist,
    build_target_playlist,
    create_playlist_from_uris,
)


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
        self.playlists: list[dict[str, object]] = []
        self.user: dict[str, object] = {"id": "user-123"}

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

    def current_user(self) -> dict[str, object]:
        return self.user

    def current_user_playlists(self, limit: int, offset: int) -> dict[str, object]:
        page = self.playlists[offset : offset + limit]
        return {"items": page, "next": None}

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


class TargetPlaylistClient(PlaylistClient):
    def __init__(
        self,
        playlist_items: list[str] | None = None,
        *,
        public: bool = True,
        owner: str = "user-123",
        collaborative: bool = False,
        total: int = 0,
    ) -> None:
        super().__init__(playlist_items=playlist_items)
        self.target = {
            "id": "1234567890123456789012",
            "uri": "spotify:playlist:1234567890123456789012",
            "name": "Existing target",
            "description": "Keep this description",
            "public": public,
            "collaborative": collaborative,
            "owner": {"id": owner},
            "tracks": {"total": total},
            "external_urls": {
                "spotify": "https://open.spotify.com/playlist/1234567890123456789012"
            },
        }

    def playlist(self, playlist_id: str, fields: str) -> dict[str, object]:
        return self.target


class AddPlaylistClient(TargetPlaylistClient):
    def __init__(
        self,
        playlist_items: list[str],
        *,
        collaborative: bool = False,
        owner: str = "user-123",
        concurrent_extra: str | None = None,
        wrong_append: bool = False,
        fail_after_write: bool = False,
    ) -> None:
        super().__init__(
            playlist_items=playlist_items,
            public=False,
            owner=owner,
            collaborative=collaborative,
            total=len(playlist_items),
        )
        self.concurrent_extra = concurrent_extra
        self.wrong_append = wrong_append
        self.fail_after_write = fail_after_write
        self.playlist_reads = 0

    def playlist(self, playlist_id: str, fields: str) -> dict[str, object]:
        self.playlist_reads += 1
        return self.target

    def playlist_add_items(self, playlist_id: str, items: Sequence[str]) -> dict[str, Any]:
        if self.wrong_append:
            self._playlist_items.extend([_track_uri(99) for _ in items])
        else:
            self._playlist_items.extend(items)
        if self.concurrent_extra is not None:
            self._playlist_items.append(self.concurrent_extra)
        self.target["tracks"] = {"total": len(self._playlist_items)}
        self.added.append({"playlist_id": playlist_id, "items": list(items)})
        if self.fail_after_write:
            raise SpotifyException(500, -1, "server error after write")
        return {"snapshot_id": "snapshot-add"}


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


def test_build_public_uses_default_suffix_and_verifies_contents() -> None:
    uris = [_track_uri(1), _track_uri(2)]
    client = PlaylistClient(playlist_items=uris)
    client.playlists = [
        {"name": "My Perfect Playlist", "owner": {"id": "user-123"}},
        {"name": "Ignored followed list", "owner": {"id": "other-user"}},
    ]

    result = build_public_playlist(TrackSequence(uris=tuple(uris)), client=client)

    assert result.playlist.name == "My Perfect Playlist (1)"
    assert client.created[0] == {
        "name": "My Perfect Playlist (1)",
        "public": True,
        "description": "Built with Perfect Playlist",
        "collaborative": False,
    }


def test_build_public_rejects_explicit_owned_name_before_creation() -> None:
    client = PlaylistClient()
    client.playlists = [{"name": "Taken", "owner": {"id": "user-123"}}]

    with pytest.raises(PlaylistCreateError, match="already own"):
        build_public_playlist(TrackSequence(uris=(_track_uri(1),)), name="Taken", client=client)

    assert client.created == []


def test_build_public_rejects_empty_sequence_before_owned_scan() -> None:
    client = PlaylistClient()

    with pytest.raises(PlaylistCreateError, match="non-empty"):
        build_public_playlist(TrackSequence(), client=client)

    assert client.created == []


def test_build_public_rejects_mismatched_readback() -> None:
    client = PlaylistClient(playlist_items=[_track_uri(2)])

    with pytest.raises(PlaylistVerificationError, match="different tracks"):
        build_public_playlist(TrackSequence(uris=(_track_uri(1),)), client=client)


def test_build_target_accepts_owned_empty_public_playlist_and_preserves_metadata() -> None:
    uris = [_track_uri(1), _track_uri(2)]
    client = TargetPlaylistClient(playlist_items=uris)

    result = build_target_playlist(
        TrackSequence(uris=tuple(uris)),
        "https://open.spotify.com/playlist/1234567890123456789012",
        client=client,
    )

    assert result.playlist.name == "Existing target"
    assert client.created == []
    assert client.added == [{"playlist_id": "1234567890123456789012", "items": uris}]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"owner": "other-user"}, "owned"),
        ({"collaborative": True}, "Collaborative"),
        ({"total": 1}, "empty"),
        ({"public": True, "private": True}, "private"),
    ],
)
def test_build_target_rejects_ineligible_targets(kwargs: dict[str, object], message: str) -> None:
    private = bool(kwargs.pop("private", False))
    total = kwargs.get("total", 0)
    if not isinstance(total, int):
        total = 0
    client = TargetPlaylistClient(
        public=bool(kwargs.get("public", True)),
        owner=str(kwargs.get("owner", "user-123")),
        collaborative=bool(kwargs.get("collaborative", False)),
        total=total,
    )

    with pytest.raises(PlaylistCreateError, match=message):
        build_target_playlist(
            TrackSequence(uris=(_track_uri(1),)),
            "spotify:playlist:1234567890123456789012",
            private=private,
            client=client,
        )

    assert client.added == []


def test_build_target_rejects_empty_sequence_before_reading_target() -> None:
    client = TargetPlaylistClient()

    with pytest.raises(PlaylistCreateError, match="non-empty"):
        build_target_playlist(
            TrackSequence(), "spotify:playlist:1234567890123456789012", client=client
        )

    assert client.added == []


@pytest.mark.parametrize("collaborative", [False, True])
def test_add_accepts_owned_or_collaborative_targets(collaborative: bool) -> None:
    existing = [_track_uri(1)]
    source = [_track_uri(2), _track_uri(3)]
    client = AddPlaylistClient(existing, collaborative=collaborative)

    result = add_to_playlist(
        TrackSequence(uris=tuple(source)),
        "spotify:playlist:1234567890123456789012",
        client=client,
    )

    assert result.added_uris == source
    assert client.added == [{"playlist_id": "1234567890123456789012", "items": source}]
    assert client.target["public"] is False


def test_add_rejects_empty_source_before_reading_target() -> None:
    client = AddPlaylistClient([_track_uri(1)])

    with pytest.raises(PlaylistAddError, match="non-empty"):
        add_to_playlist(TrackSequence(), "spotify:playlist:1234567890123456789012", client=client)

    assert client.playlist_reads == 0
    assert client.added == []


def test_add_rejects_non_owned_non_collaborative_target() -> None:
    client = AddPlaylistClient([_track_uri(1)], owner="other-user")

    with pytest.raises(PlaylistAddError, match="permit"):
        add_to_playlist(
            TrackSequence(uris=(_track_uri(2),)),
            "spotify:playlist:1234567890123456789012",
            client=client,
        )

    assert client.added == []


@pytest.mark.parametrize(
    ("concurrent_extra", "wrong_append", "message"),
    [
        (_track_uri(9), False, "changed concurrently"),
        (None, True, "appended tracks could not be verified"),
    ],
)
def test_add_rejects_concurrent_or_unverified_append(
    concurrent_extra: str | None, wrong_append: bool, message: str
) -> None:
    client = AddPlaylistClient(
        [_track_uri(1)], concurrent_extra=concurrent_extra, wrong_append=wrong_append
    )

    with pytest.raises(PlaylistVerificationError, match=message):
        add_to_playlist(
            TrackSequence(uris=(_track_uri(2),)),
            "spotify:playlist:1234567890123456789012",
            client=client,
        )


def test_add_surfaces_partial_write_without_success() -> None:
    client = AddPlaylistClient([_track_uri(1)], fail_after_write=True)

    with pytest.raises(PlaylistAddError, match="chunk 1"):
        add_to_playlist(
            TrackSequence(uris=(_track_uri(2),)),
            "spotify:playlist:1234567890123456789012",
            client=client,
        )

    assert client.added == [
        {"playlist_id": "1234567890123456789012", "items": [_track_uri(2)]}
    ]
