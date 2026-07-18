# Perfect Playlist

Build the Spotify playlist you chose, exactly as you chose it.

Perfect Playlist is a local CLI and importable Python package for turning an ordered set of exact Spotify track references into an exact playlist. It preserves order and duplicates, validates before writing, and verifies what Spotify stored afterward.

## Vision

AI should be able to build a deterministic playlist without outsourcing the final decision to another generative system. Perfect Playlist is intended to become that dependable final-mile primitive for both people and AI agents.

## Mission

Provide the smallest safe interface that can discover Spotify tracks, inspect exact candidates, preserve a chosen TrackSequence, and build or compare playlists without substitution, hidden reordering, silent skips, or destructive overwrites.

## Why This Exists

The idea came from trying to create deterministic playlists through ChatGPT's Spotify integration. Asking ChatGPT to ask Spotify to "generate" a playlist passes the intent through multiple interpretive layers. It is like playing a game of Telephone with AI: the request may sound similar at the other end, but the exact tracks and order are no longer guaranteed.

Perfect Playlist removes that last interpretive handoff. An AI agent can search, inspect, and deliberately select exact Spotify track references, then hand the resulting TrackSequence to a deterministic build command. Discovery can be intelligent; the final write should be exact.

This project is not trying to replace recommendation systems. It provides the reliable mechanism that builds a playlist after the choices have already been made.

## Product Direction

- `build` is the primary action and creates a new public playlist by default.
- A public or private playlist can be built by supplying an owned, empty target.
- `add` is a secondary, append-only action and never changes visibility.
- `verify` compares any two Sources as exact ordered TrackSequences.
- `export` creates durable YAML, JSON, text, or link output without overwriting files.
- `search` and `inspect` expose facts without choosing tracks or writing playlists.
- Repair and natural-language resolve workflows are removed from the interface.

The approved behavior is specified in [the CLI contract](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/CLI-CONTRACT.md). The canonical TrackSequence, Source pipeline, authentication behavior, deterministic write workflows, read-only discovery commands, agent guidance, and offline/live QA matrix are complete.

## Documentation

- [Product vision and ubiquitous language](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/PRODUCT-AND-LANGUAGE.md)
- [Authoritative CLI contract](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/CLI-CONTRACT.md)
- [Reconciled implementation plan](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/IMPLEMENTATION-PLAN.md)
- [Git completion workflow](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/GIT-WORKFLOW.md)
- [Live Spotify QA evidence and handoff](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/LIVE-QA.md)

Start with [the documentation index](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/README.md) when implementing or reviewing the project.

## Requirements

- Python 3.11+
- A Spotify developer app
- A registered loopback redirect URI such as `http://127.0.0.1:8888/callback`

## Installation

Install the released command and Python package from PyPI:

```powershell
python -m pip install perfect-playlist
perfect-playlist --help
```

Create a private environment file outside the package installation:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

Point Perfect Playlist to that file, then authorize the Spotify account once:

```powershell
$env:PERFECT_PLAYLIST_SECRETS_FILE='C:\path\to\spotify-secrets.env'
perfect-playlist auth login
```

Keep `PERFECT_PLAYLIST_SECRETS_FILE` set whenever you run the CLI, or set the three `SPOTIPY_*` variables directly. OAuth tokens are stored separately in the operating-system user cache.

## Development Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
New-Item -ItemType Directory -Force resources | Out-Null
Copy-Item spotify-secrets.env.example resources/spotify-secrets.env
```

Populate the local, gitignored `resources/spotify-secrets.env`:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=0
```

The package loads this file directly with `python-dotenv`. The safe committed shape is `spotify-secrets.env.example`; Ralph-specific configuration is documented in the [repository setup guide](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/README-RALPH.md). The real file, its values, OAuth material, and token caches must never be committed.

Register the exact redirect URI in Spotify's developer dashboard, then authorize once:

```powershell
perfect-playlist auth login
```

OAuth tokens are stored outside the repository in the operating-system user cache.

## Usage

Use Search and Inspect to choose exact tracks, store the chosen canonical URIs in a durable Source, and pass that Source to write commands:

```yaml
tracks:
  - spotify:track:5Qamlcya1Hz5Z4AgzdQ5q8
  - spotify:track:5irdISp39LC6kD10muguYh
```

```powershell
perfect-playlist search 'track:"Call On You" artist:"Corey Lingo"'
perfect-playlist inspect spotify:track:5Qamlcya1Hz5Z4AgzdQ5q8
perfect-playlist build tracks.yaml
perfect-playlist add tracks.yaml --target spotify:playlist:PLAYLIST_ID
perfect-playlist verify tracks.yaml spotify:playlist:PLAYLIST_ID
perfect-playlist export spotify:playlist:PLAYLIST_ID --out playlist.yaml
```

With no `--name` or `--target`, Build creates a new public `My Perfect Playlist`, advancing to a numeric suffix if that name is already owned. Use `--target` only for an owned empty Build Target; Add requires `--target` and appends without changing earlier tracks or visibility.

The importable API exposes the same workflow boundaries and typed results:

```python
from perfect_playlist import (
    add_to_playlist,
    build_public_playlist,
    build_target_playlist,
    compare_track_sequences,
    inspect_track,
    read_source,
    search_tracks,
)

source = read_source("tracks.yaml")
candidates = search_tracks('track:"Call On You" artist:"Corey Lingo"')
selected = inspect_track(candidates[0].uri)
built = build_public_playlist(source)
target_build = build_target_playlist(source, "spotify:playlist:PLAYLIST_ID")
added = add_to_playlist(source, "spotify:playlist:WRITABLE_PLAYLIST_ID")
verification = compare_track_sequences(source, read_source(built.playlist.uri))
```

Search results and inspected metadata are command responses, not Sources. The caller deliberately chooses canonical URIs before Build or Add.

## Current Validation

Offline checks:

```powershell
$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS='0'
python -m pytest
python -m ruff check --no-cache perfect_playlist tests
python -m mypy --no-incremental perfect_playlist tests
```

The live Spotify test is controlled by `resources/spotify-secrets.env`. Set
`PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1` to include a temporary public
create/verify/unfollow cycle in every full pytest run. Leave it at `0` to keep
live writes opt-in.

```powershell
$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS='1'
python -m pytest
```

The latest credentialed run proved public creation and exact ordered writes, but Spotify did not persist a requested private state during API creation. The package now fails closed before adding tracks. The approved private flow therefore fills an empty private playlist that the user already owns instead of claiming that the API can create one reliably. See [live QA evidence](https://github.com/devin-thomas/perfect-playlist/blob/main/docs/LIVE-QA.md).

## Determinism Policy

Write operations accept only Sources that resolve to exact Spotify track URIs. Human-readable song requests belong in an agent's discovery workflow, where Search and Inspect can be used deliberately. They are never silently resolved inside Build or Add.
