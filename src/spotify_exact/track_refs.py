from __future__ import annotations

import re
from urllib.parse import urlparse

from .errors import InvalidTrackRefError

TRACK_ID_RE = re.compile(r"^[A-Za-z0-9]{22}$")
TRACK_URI_RE = re.compile(r"^spotify:track:(?P<id>[A-Za-z0-9]{22})$")


def extract_track_id(value: str) -> str:
    """Extract a Spotify track id from an exact track URI or open.spotify.com URL."""
    candidate = value.strip()
    uri_match = TRACK_URI_RE.fullmatch(candidate)
    if uri_match:
        return uri_match.group("id")

    parsed = urlparse(candidate)
    if parsed.scheme in {"http", "https"} and parsed.netloc == "open.spotify.com":
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "track" and TRACK_ID_RE.fullmatch(parts[1]):
            return parts[1]

    raise InvalidTrackRefError(f"Expected a Spotify track URI or URL: {value}")


def normalize_track_ref(value: str) -> str:
    """Return spotify:track:<id> from a Spotify track URI or open.spotify.com track URL."""
    return f"spotify:track:{extract_track_id(value)}"


def is_track_uri(value: str) -> bool:
    """Return whether a value is already a Spotify track URI."""
    return TRACK_URI_RE.fullmatch(value.strip()) is not None

