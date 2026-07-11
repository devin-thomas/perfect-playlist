class SpotifyExactError(Exception):
    """Base exception for perfect-playlist."""


class InvalidTrackRefError(SpotifyExactError):
    """Raised when a value is not an exact Spotify track reference."""


class PlaylistCreateError(SpotifyExactError):
    """Raised when playlist creation fails."""


class PlaylistAddError(SpotifyExactError):
    """Raised when adding a track batch fails."""


class PlaylistVerificationError(SpotifyExactError):
    """Raised when playlist order does not match the expected URI order."""


class AuthConfigError(SpotifyExactError):
    """Raised when Spotify auth configuration is missing or invalid."""


class ManifestError(SpotifyExactError):
    """Raised when a playlist manifest is malformed or invalid."""


class SpotifyApiError(SpotifyExactError):
    """Raised when Spotify or Spotipy rejects an API operation."""


class TrackLookupError(SpotifyApiError):
    """Raised when track search or metadata lookup fails."""
