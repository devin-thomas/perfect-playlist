from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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

