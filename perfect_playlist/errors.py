class SpotifyExactError(Exception):
    """Base exception for perfect-playlist."""


class InvalidTrackRefError(SpotifyExactError):
    """Raised when a value is not an exact Spotify track reference."""


class PlaylistCreateError(SpotifyExactError):
    """Raised when playlist creation fails."""


class PlaylistVerificationError(SpotifyExactError):
    """Raised when Spotify does not store the requested playlist contents."""


class PlaylistAddError(SpotifyExactError):
    """Raised when adding a track batch fails."""


class AuthConfigError(SpotifyExactError):
    """Raised when Spotify auth configuration is missing or invalid."""


class SpotifyAuthenticationRequiredError(SpotifyExactError):
    """Raised when a command needs Spotify authorization but cannot open a browser."""


class SourceError(SpotifyExactError):
    """Raised when a durable TrackSequence Source is malformed or unsupported."""


class SourceMalformedError(SourceError):
    """Raised when a Source reference or document is malformed."""


class SourceAccessError(SourceError):
    """Raised when a referenced Spotify resource cannot be read."""


class SourceAuthenticationError(SourceError):
    """Raised when Spotify authentication is required or rejected."""


class SourceSpotifyError(SourceError):
    """Raised when Spotify fails while resolving a Source."""


class ExportError(SpotifyExactError):
    """Raised when a TrackSequence cannot be exported safely."""


class SpotifyApiError(SpotifyExactError):
    """Raised when Spotify or Spotipy rejects an API operation."""


class TrackLookupError(SpotifyApiError):
    """Raised when track search or metadata lookup fails."""
