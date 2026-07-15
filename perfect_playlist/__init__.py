"""Public API for perfect-playlist."""

from .io import read_source, read_spotify_source, read_uri_lines
from .models import (
    CreatedPlaylist,
    PlaylistAddResult,
    PlaylistCreateResult,
    TrackSequence,
    TrackSummary,
)
from .playlist import (
    add_items_in_order,
    add_to_playlist,
    build_public_playlist,
    build_target_playlist,
    chunked,
    create_empty_playlist,
    create_playlist_from_uris,
)
from .search import get_tracks, search_tracks
from .track_refs import (
    extract_playlist_id,
    extract_track_id,
    is_raw_spotify_id,
    is_track_uri,
    normalize_playlist_ref,
    normalize_track_ref,
)

__all__ = [
    "CreatedPlaylist",
    "PlaylistAddResult",
    "PlaylistCreateResult",
    "TrackSequence",
    "TrackSummary",
    "add_items_in_order",
    "add_to_playlist",
    "build_target_playlist",
    "build_public_playlist",
    "chunked",
    "create_empty_playlist",
    "create_playlist_from_uris",
    "extract_track_id",
    "extract_playlist_id",
    "get_tracks",
    "is_track_uri",
    "is_raw_spotify_id",
    "normalize_track_ref",
    "normalize_playlist_ref",
    "read_source",
    "read_spotify_source",
    "read_uri_lines",
    "search_tracks",
]
