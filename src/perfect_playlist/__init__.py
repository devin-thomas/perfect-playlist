"""Public API for perfect-playlist."""

from .io import read_manifest, read_uri_lines
from .models import (
    CreatedPlaylist,
    PlaylistCreateResult,
    PlaylistManifest,
    PlaylistManifestTrack,
    TrackRef,
    TrackSummary,
)
from .playlist import (
    add_items_in_order,
    chunked,
    create_empty_playlist,
    create_playlist_from_file,
    create_playlist_from_uris,
)
from .search import get_tracks, search_tracks
from .track_refs import extract_track_id, is_track_uri, normalize_track_ref
from .verify import export_playlist_to_file, verify_playlist_prefix

__all__ = [
    "CreatedPlaylist",
    "PlaylistCreateResult",
    "PlaylistManifest",
    "PlaylistManifestTrack",
    "TrackRef",
    "TrackSummary",
    "add_items_in_order",
    "chunked",
    "create_empty_playlist",
    "create_playlist_from_file",
    "create_playlist_from_uris",
    "extract_track_id",
    "export_playlist_to_file",
    "get_tracks",
    "is_track_uri",
    "normalize_track_ref",
    "read_manifest",
    "read_uri_lines",
    "search_tracks",
    "verify_playlist_prefix",
]
