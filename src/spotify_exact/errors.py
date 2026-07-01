class SpotifyExactError(Exception):
    """Base exception for spotify-exact."""


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

