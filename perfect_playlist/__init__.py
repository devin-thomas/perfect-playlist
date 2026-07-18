"""Public TrackSequence API for deterministic Spotify playlist workflows."""

from .errors import (
    AuthConfigError,
    ExportError,
    InvalidTrackRefError,
    PlaylistAddError,
    PlaylistCreateError,
    PlaylistVerificationError,
    SourceAccessError,
    SourceAuthenticationError,
    SourceError,
    SourceMalformedError,
    SourceSpotifyError,
    SpotifyApiError,
    SpotifyAuthenticationRequiredError,
    SpotifyExactError,
    TrackLookupError,
)
from .export import next_available_path, serialize, track_links, write_export
from .io import read_source, read_spotify_source, read_uri_lines
from .models import (
    CreatedPlaylist,
    PlaylistAddResult,
    PlaylistCreateResult,
    SourceVerificationResult,
    TrackSequence,
    TrackSummary,
)
from .playlist import (
    add_to_playlist,
    build_public_playlist,
    build_target_playlist,
)
from .search import inspect_track, search_tracks
from .track_refs import (
    extract_playlist_id,
    extract_track_id,
    is_raw_spotify_id,
    is_track_uri,
    normalize_playlist_ref,
    normalize_track_ref,
)
from .verify import compare_track_sequences

__all__ = [
    "CreatedPlaylist",
    "AuthConfigError",
    "ExportError",
    "InvalidTrackRefError",
    "PlaylistAddResult",
    "PlaylistAddError",
    "PlaylistCreateResult",
    "PlaylistCreateError",
    "PlaylistVerificationError",
    "SourceAccessError",
    "SourceAuthenticationError",
    "SourceError",
    "SourceMalformedError",
    "SourceSpotifyError",
    "SourceVerificationResult",
    "SpotifyApiError",
    "SpotifyAuthenticationRequiredError",
    "SpotifyExactError",
    "TrackSequence",
    "TrackSummary",
    "TrackLookupError",
    "add_to_playlist",
    "build_target_playlist",
    "build_public_playlist",
    "extract_track_id",
    "extract_playlist_id",
    "inspect_track",
    "is_track_uri",
    "is_raw_spotify_id",
    "normalize_track_ref",
    "normalize_playlist_ref",
    "read_source",
    "read_spotify_source",
    "read_uri_lines",
    "next_available_path",
    "serialize",
    "search_tracks",
    "track_links",
    "write_export",
    "compare_track_sequences",
]
