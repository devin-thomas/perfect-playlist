from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import InvalidTrackRefError
from .track_refs import normalize_track_ref


class TrackRef(BaseModel):
    uri: str
    id: str
    kind: Literal["track"] = "track"


class TrackSummary(BaseModel):
    uri: str
    url: str
    title: str
    artists: list[str]
    album: str | None = None
    duration_ms: int | None = None
    explicit: bool | None = None


class CreatedPlaylist(BaseModel):
    id: str
    uri: str
    url: str
    name: str
    snapshot_id: str | None = None


class PlaylistCreateResult(BaseModel):
    playlist: CreatedPlaylist
    added_uris: list[str]
    verified: bool | None = None
    warnings: list[str] = Field(default_factory=list)


class PlaylistRepairResult(BaseModel):
    playlist_id: str
    expected_uris: list[str]
    actual_uris: list[str]
    changed: bool
    applied: bool
    snapshot_id: str | None = None


class PlaylistManifestTrack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    artist: str
    uri: str | None = None
    missing: bool = False
    note: str | None = None

    @model_validator(mode="after")
    def validate_reference(self) -> PlaylistManifestTrack:
        if self.missing and self.uri is not None:
            raise ValueError("cannot include uri when missing: true")
        if not self.missing and self.uri is None:
            raise ValueError("must include uri or set missing: true")
        if self.uri is not None:
            try:
                self.uri = normalize_track_ref(self.uri)
            except InvalidTrackRefError as exc:
                raise ValueError("uri must be a Spotify track URI or URL") from exc
        return self


class PlaylistManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    public: bool = False
    description: str = ""
    tracks: list[PlaylistManifestTrack]

    @property
    def uris(self) -> list[str]:
        """Return only verified track URIs, preserving manifest order."""
        return [track.uri for track in self.tracks if track.uri is not None]
