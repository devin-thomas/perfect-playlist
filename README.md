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
- Repair and natural-language resolve workflows are removed from the next interface.

The approved next CLI is specified in [the CLI contract](docs/CLI-CONTRACT.md). The repository still contains portions of the earlier grouped command implementation while that contract is being implemented; do not treat the new command examples as shipped until the implementation plan and checks are complete.

## Documentation

- [Product vision and ubiquitous language](docs/PRODUCT-AND-LANGUAGE.md)
- [Authoritative CLI contract](docs/CLI-CONTRACT.md)
- [Reconciled implementation plan](docs/IMPLEMENTATION-PLAN.md)
- [Live Spotify QA evidence and handoff](docs/LIVE-QA.md)
- [LinkedIn progress-post draft](docs/LINKEDIN-DRAFT.md)

Start with [the documentation index](docs/README.md) when implementing or reviewing the project.

## Requirements

- Python 3.11+
- A Spotify developer app
- A registered loopback redirect URI such as `http://127.0.0.1:8888/callback`

## Development Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,yaml]"
Copy-Item .env.example .env
```

Populate the local, gitignored `.env`:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

The package already loads this file with `python-dotenv`. Project maintainers also have a private credential note at `C:\dev\personal\spotify-playlist-modify\resources\secrets.md`; it stays gitignored and must never be committed. Copy values into `.env` locally rather than changing code to parse the Markdown file.

Register the exact redirect URI in Spotify's developer dashboard, then authorize once:

```powershell
perfect-playlist auth login
```

OAuth tokens are stored outside the repository in the operating-system user cache.

## Current Validation

Offline checks:

```powershell
python -m pytest
python -m ruff check --no-cache src tests
python -m mypy src
```

The live Spotify test is deliberately opt-in:

```powershell
$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS="1"
python -m pytest tests/integration
```

The latest credentialed run proved public creation and exact ordered writes, but Spotify did not persist a requested private state during API creation. The package now fails closed before adding tracks. The approved private flow therefore fills an empty private playlist that the user already owns instead of claiming that the API can create one reliably. See [live QA evidence](docs/LIVE-QA.md).

## Determinism Policy

Write operations accept only Sources that resolve to exact Spotify track URIs. Human-readable song requests belong in an agent's discovery workflow, where Search and Inspect can be used deliberately. They are never silently resolved inside Build or Add.
