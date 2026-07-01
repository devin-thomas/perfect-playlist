"""Public API for perfect-playlist."""

from .io import read_uri_lines
from .models import CreatedPlaylist, PlaylistCreateResult, TrackRef, TrackSummary
from .playlist import (
    add_items_in_order,
    chunked,
    create_empty_playlist,
    create_playlist_from_file,
    create_playlist_from_uris,
)
from .search import get_tracks, search_tracks
from .track_refs import extract_track_id, is_track_uri, normalize_track_ref
from .verify import verify_playlist_prefix

__all__ = [
    "CreatedPlaylist",
    "PlaylistCreateResult",
    "TrackRef",
    "TrackSummary",
    "add_items_in_order",
    "chunked",
    "create_empty_playlist",
    "create_playlist_from_file",
    "create_playlist_from_uris",
    "extract_track_id",
    "get_tracks",
    "is_track_uri",
    "normalize_track_ref",
    "read_uri_lines",
    "search_tracks",
    "verify_playlist_prefix",
]

