from __future__ import annotations

from collections.abc import Sequence
from typing import overload

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import InvalidTrackRefError
from .track_refs import normalize_track_ref


class TrackSequence(BaseModel):
    """An immutable, ordered sequence of canonical Spotify track URIs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    uris: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def normalize_uris(cls, data: object) -> object:
        if not isinstance(data, dict):
            raise TypeError("TrackSequence must be constructed with an 'uris' field")

        raw_uris = data.get("uris", ())
        if isinstance(raw_uris, (str, bytes)) or not isinstance(raw_uris, Sequence):
            raise TypeError("uris must be a sequence of Spotify track references")

        normalized: list[str] = []
        for index, value in enumerate(raw_uris):
            if not isinstance(value, str):
                raise TypeError(f"uris[{index}] must be a Spotify track URI or URL")
            try:
                normalized.append(normalize_track_ref(value))
            except InvalidTrackRefError as exc:
                raise ValueError(f"uris[{index}] must be a Spotify track URI or URL") from exc

        return {**data, "uris": tuple(normalized)}

    def __len__(self) -> int:
        return len(self.uris)

    @overload
    def __getitem__(self, index: int) -> str: ...

    @overload
    def __getitem__(self, index: slice) -> tuple[str, ...]: ...

    def __getitem__(self, index: int | slice) -> str | tuple[str, ...]:
        return self.uris[index]


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


class PlaylistAddResult(BaseModel):
    playlist: CreatedPlaylist
    added_uris: list[str]
