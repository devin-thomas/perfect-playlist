# Perfect Playlist: Product and Language

## Vision

Make deterministic playlist building a dependable primitive for people and AI agents: exact tracks, exact order, no substitutions, and no ambiguity about what Spotify will receive.

## Mission

Perfect Playlist turns a durable Source into an exact Spotify playlist through a small, safe CLI and importable Python package. It separates discovery from choice, validates before writing, verifies after writing, and refuses destructive or uncertain behavior.

## Origin

The project began with a practical frustration: asking ChatGPT to ask its Spotify integration to "generate" a playlist does not provide a deterministic result. The prompt passes through multiple interpretive layers before Spotify receives a request. It is like playing a game of Telephone with AI: each handoff can change the meaning, tracks, or order.

Perfect Playlist removes that chain. An AI agent can search and inspect candidates, deliberately choose exact Spotify track references, store them as a TrackSequence, and then build precisely that sequence. The product is not another playlist generator. It is the reliable final-mile tool that builds the playlist already decided upon.

## Product Principles

- Build, do not generate: writes use exact track references in exact order.
- One portable data type: TrackSequence is the only playlist data passed between commands and agents.
- Discovery never chooses: Search and Inspect provide facts; the caller makes the selection.
- Safe writes: Build writes only to a new public playlist or an owned empty target; Add is append-only.
- Verify outcomes: successful writes are read back and checked.
- Fail clearly: invalid, ambiguous, inaccessible, or unsafe operations stop with actionable errors.
- Agent-ready, human-readable: the interface is deterministic for automation and understandable at a terminal.

## Ubiquitous Language

**Playlist**:
The sole user-facing object: an ordered Spotify collection built from exact track references.
_Avoid_: Playlist object, collection

**Deterministic**:
The same exact ordered track references produce the same ordered playlist without prompting, substitution, recommendation, or generative interpretation.
_Avoid_: Generated, recommended, close enough

**Playlist Name**:
A case-sensitive name considered taken only when the signed-in user already owns a public or private playlist with the same name.
_Avoid_: Identifier, case-insensitive name

**Build**:
The primary product action: produce the finished playlist from a Source in exact order by filling an owned empty build target, or by creating a new public playlist when no target is supplied.
_Avoid_: Create, fill, generate

**Add**:
Append and verify a Source's TrackSequence at the end of any playlist the signed-in user may modify, whether owned or collaborative, public or private, without changing its visibility or promising its earlier contents.
_Avoid_: Build, insert, prepend

**Build Target**:
An empty public or private playlist owned by the signed-in user and supplied as the destination for a build. A target is optional for public build and required for private build.
_Avoid_: Collaborative playlist, writable playlist, private link

**Target**:
The playlist that receives a write. Build and Add use different eligibility rules for their targets.
_Avoid_: Destination, `--to`

**Writable Playlist**:
An existing public or private playlist that Spotify permits the signed-in user to modify, either through ownership or collaboration.
_Avoid_: Build target, owned playlist

**Verify**:
Prove that two sources resolve to identical TrackSequences with the same tracks, order, and count. Neither source is privileged as expected or actual, and source ownership is irrelevant.
_Avoid_: Check, validate, prefix verification

**Verified**:
The successful outcome when two sources resolve to identical TrackSequences.
_Avoid_: Match, equal, passed

**TrackSequence**:
The sole portable playlist data type: an ordered list of canonical Spotify track URIs used for building, adding, exporting, and exact comparison. Order and duplicates are preserved; all metadata is outside the TrackSequence.
_Avoid_: URI list, track list, normalized playlist

**Links**:
A text-only export view that renders each TrackSequence URI as its corresponding `open.spotify.com` track URL without changing the TrackSequence itself.
_Avoid_: Link format, link TrackSequence, URL sequence

**Source**:
Any auto-detected value that resolves to a TrackSequence: a YAML, JSON, or plain-text file; a Spotify playlist URL or URI; or a single Spotify track URL or URI.
_Avoid_: Input type, format, left side, right side

**Export**:
Render a Source's TrackSequence in a selected portable representation.
_Avoid_: Download, save

**Report**:
A future human-readable rendering of a Source enriched with descriptive Spotify metadata such as track title and artist.
_Avoid_: Export, TrackSequence

**Search**:
Find Spotify track candidates without changing a playlist.
_Avoid_: Find, lookup

**Inspect**:
Show Spotify metadata for one exact track reference.
_Avoid_: Show, track show
