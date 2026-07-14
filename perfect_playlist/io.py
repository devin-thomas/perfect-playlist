from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml
from pydantic import ValidationError
from spotipy.exceptions import SpotifyOauthError

from .client import SPOTIFY_API_EXCEPTIONS, SourceClient, get_spotify_client
from .errors import (
    AuthConfigError,
    InvalidTrackRefError,
    SourceAccessError,
    SourceAuthenticationError,
    SourceError,
    SourceMalformedError,
    SourceSpotifyError,
    SpotifyAuthenticationRequiredError,
)
from .models import TrackSequence
from .track_refs import (
    extract_playlist_id,
    extract_track_id,
    is_raw_spotify_id,
    normalize_track_ref,
)


def read_uri_lines(path: str | Path) -> list[str]:
    """Read exact Spotify track references from a text file."""
    source = Path(path)
    uris: list[str] = []

    lines = source.read_text(encoding="utf-8").splitlines()
    for line_number, raw_line in enumerate(lines, start=1):
        value = raw_line.strip()
        if not value or value.startswith("#"):
            continue
        try:
            uris.append(normalize_track_ref(value))
        except InvalidTrackRefError as exc:
            msg = f"Line {line_number} is not a Spotify track URI or URL: {value}"
            raise InvalidTrackRefError(msg) from exc

    return uris


def read_source(
    source: str | Path,
    *,
    client: SourceClient | None = None,
) -> TrackSequence:
    """Read a supported local Source into the canonical TrackSequence type."""
    if isinstance(source, str):
        value = source.strip()
        if value == "-":
            raise SourceMalformedError("Stdin '-' is not a Source; provide a durable local file.")
        if is_raw_spotify_id(value):
            raise SourceMalformedError(
                "Raw Spotify track ids are not Sources; use a typed spotify:track URI or "
                "open.spotify.com track link."
            )
        if _is_spotify_reference(value):
            return read_spotify_source(value, client=client)
        if _is_http_url(value):
            raise SourceMalformedError(
                "Remote YAML, JSON, and text documents are not Sources; download the document "
                "locally and pass the resulting file."
            )

    source = Path(source)
    suffix = source.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        data = _read_yaml_or_json(source, yaml.safe_load)
    elif suffix == ".json":
        data = _read_yaml_or_json(source, json.loads)
    elif suffix == ".txt":
        try:
            return TrackSequence(uris=tuple(read_uri_lines(source)))
        except OSError as exc:
            raise SourceError(f"Could not read Source {source}: {exc}") from exc
        except InvalidTrackRefError as exc:
            raise SourceError(f"Invalid track reference in Source {source}: {exc}") from exc
    elif not suffix:
        raise SourceMalformedError(
            f"Source {source} has no extension; supported extensions are .yaml, .yml, .json, "
            "and .txt"
        )
    else:
        raise SourceMalformedError(
            f"Unsupported Source extension {suffix!r} for {source}; supported extensions are "
            ".yaml, .yml, .json, and .txt"
        )

    if not isinstance(data, dict):
        raise SourceError(f"Source {source} must contain an object with a top-level tracks array")
    raw_tracks = data.get("tracks")
    if not isinstance(raw_tracks, list):
        raise SourceError(f"Source {source} must contain a top-level tracks array")

    references: list[str] = []
    for index, entry in enumerate(raw_tracks):
        if isinstance(entry, str):
            references.append(entry)
        elif isinstance(entry, dict) and isinstance(entry.get("uri"), str):
            references.append(entry["uri"])
        else:
            raise SourceError(
                f"Source {source} tracks[{index}] must be a Spotify track URI/link "
                "or an object with a string uri"
            )

    try:
        return TrackSequence(uris=tuple(references))
    except (TypeError, ValidationError) as exc:
        if isinstance(exc, ValidationError):
            errors = exc.errors(include_url=False)
            detail = str(errors[0].get("msg", "invalid track reference")) if errors else str(exc)
        else:
            detail = str(exc)
        raise SourceMalformedError(f"Invalid track reference in Source {source}: {detail}") from exc


def read_spotify_source(
    value: str,
    *,
    client: SourceClient | None = None,
) -> TrackSequence:
    """Read a Spotify playlist or track reference without changing it."""
    try:
        if value.startswith("spotify:track:") or "/track/" in value:
            track_id = extract_track_id(value)
            sp = client or get_spotify_client()
            track = _require_mapping(
                sp.track(track_id),
                f"Spotify returned an invalid track response for Source {value}.",
            )
            uri = track.get("uri")
            if not isinstance(uri, str):
                raise SourceAccessError(f"Spotify track {value} has no track URI.")
            return TrackSequence(
                uris=(
                    _normalize_spotify_track_uri(
                        uri,
                        f"Spotify returned an invalid track URI for Source {value}.",
                    ),
                )
            )

        playlist_id = extract_playlist_id(value)
        sp = client or get_spotify_client()
        return TrackSequence(uris=tuple(_read_playlist_uris(playlist_id, sp)))
    except (AuthConfigError, SpotifyAuthenticationRequiredError) as exc:
        raise SourceAuthenticationError(str(exc)) from exc
    except SpotifyOauthError as exc:
        raise SourceAuthenticationError(
            f"Spotify authentication failed while resolving Source {value}."
        ) from exc
    except SourceError:
        raise
    except SPOTIFY_API_EXCEPTIONS as exc:
        status = getattr(exc, "http_status", None)
        if status in {401, 403}:
            raise SourceAuthenticationError(
                f"Spotify authentication is required to read Source {value}."
            ) from exc
        if status == 404:
            raise SourceAccessError(f"Spotify Source is inaccessible: {value}") from exc
        raise SourceSpotifyError(f"Spotify failed while resolving Source {value}.") from exc
    except InvalidTrackRefError as exc:
        raise SourceMalformedError(str(exc)) from exc


def _read_playlist_uris(playlist_id: str, client: SourceClient) -> list[str]:
    uris: list[str] = []
    offset = 0
    while True:
        try:
            response = _require_mapping(
                client.playlist_items(
                    playlist_id,
                    fields="items(track(uri)),next",
                    limit=100,
                    offset=offset,
                ),
                f"Spotify returned an invalid response for playlist {playlist_id}.",
            )
        except SPOTIFY_API_EXCEPTIONS:
            raise
        items = response.get("items")
        if not isinstance(items, list):
            raise SourceSpotifyError(
                f"Spotify returned invalid items for playlist {playlist_id}."
            )
        for index, item in enumerate(items):
            if not isinstance(item, Mapping):
                raise SourceAccessError(
                    f"Spotify playlist {playlist_id} contains an inaccessible track at "
                    f"position {offset + index + 1}."
                )
            track = item.get("track")
            if not isinstance(track, Mapping):
                raise SourceAccessError(
                    f"Spotify playlist {playlist_id} contains an inaccessible track at "
                    f"position {offset + index + 1}."
                )
            uri = track.get("uri")
            if not isinstance(uri, str):
                raise SourceAccessError(
                    f"Spotify playlist {playlist_id} contains an inaccessible track at "
                    f"position {offset + index + 1}."
                )
            uris.append(
                _normalize_spotify_track_uri(
                    uri,
                    f"Spotify returned an invalid track URI for playlist {playlist_id} at "
                    f"position {offset + index + 1}.",
                )
            )
        if response.get("next") is None:
            return uris
        if not items:
            raise SourceSpotifyError(f"Spotify returned an empty page for playlist {playlist_id}.")
        offset += len(items)


def _require_mapping(value: object, message: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SourceSpotifyError(message)
    return value


def _normalize_spotify_track_uri(value: str, message: str) -> str:
    try:
        return normalize_track_ref(value)
    except InvalidTrackRefError as exc:
        raise SourceSpotifyError(message) from exc


def _is_spotify_reference(value: str) -> bool:
    return value.startswith("spotify:") or "open.spotify.com/" in value


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _read_yaml_or_json(source: Path, loader: Callable[[str], object]) -> object:
    try:
        text = source.read_text(encoding="utf-8")
        return loader(text)
    except OSError as exc:
        raise SourceError(f"Could not read Source {source}: {exc}") from exc
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise SourceError(f"Could not parse Source {source}: {exc}") from exc
