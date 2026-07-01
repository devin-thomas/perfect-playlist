# spotify-exact

Deterministic Spotify playlist creation from exact track URIs.

`spotify-exact` is a local CLI and importable Python package for creating Spotify playlists from an ordered list of exact Spotify track URIs or track URLs. It does not search, substitute, reorder, or silently skip tracks during playlist creation.

## Why This Exists

Spotify playlist generation tools often optimize for recommendations or fuzzy matching. This project optimizes for repeatability:

- input order is preserved
- duplicate tracks are allowed
- invalid lines fail before Spotify write operations
- add operations are chunked in Spotify's 100-item batches
- fuzzy search is kept separate from deterministic playlist writes

## Requirements

- Python 3.11+
- A Spotify developer app
- A redirect URI using a loopback IP literal, for example `http://127.0.0.1:8888/callback`

## Setup

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,yaml]"
Copy-Item .env.example .env
```

Edit `.env` with your Spotify app credentials:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

## Fast Path

Create a text file containing one exact track URI or Spotify track URL per line:

```text
# The Paradox Tiny Desk - verified available tracks
spotify:track:354WZaV3u6cuzTG2PmpYwm
spotify:track:78APbsosmvDYIwZHjzC5ZE
spotify:track:1OAMZ1AV5y6DHI5kzP0L3V
spotify:track:6FVeZfWkYtDiyyq93dBSXU
spotify:track:1y6lq1wrAspWEgRJmYb11S
```

Dry run first:

```powershell
spotify-exact playlist create "The Paradox Tiny Desk - Available Tracks" --private --from examples/paradox-tiny-desk.txt --dry-run
```

Create the playlist:

```powershell
spotify-exact playlist create "The Paradox Tiny Desk - Available Tracks" --private --from examples/paradox-tiny-desk.txt --verify
```

## CLI Shape

```text
spotify-exact
  auth
    login
    status
  search
    track QUERY
  track
    show URI_OR_URL
  playlist
    create NAME --from FILE [--private/--public] [--dry-run] [--verify]
    add PLAYLIST_ID --from FILE [--position N]
    verify PLAYLIST_ID --from FILE
```

`playlist create`, `playlist add`, `playlist verify`, `search track`, and `track show` are implemented. Spotify write operations still require valid credentials and a configured Spotify developer app.

## Library Usage

```python
from spotify_exact import create_playlist_from_uris

result = create_playlist_from_uris(
    name="My Exact Playlist",
    uris=[
        "spotify:track:354WZaV3u6cuzTG2PmpYwm",
        "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE?si=abc123",
    ],
    public=False,
    dry_run=True,
)

print(result.added_uris)
```

## Project Structure

```text
src/spotify_exact/
  auth.py         OAuth manager setup
  client.py       Spotify client factory
  cli.py          Thin Typer CLI
  config.py       Environment and cache path helpers
  errors.py       Package exceptions
  io.py           Input file parsing
  models.py       Pydantic models
  playlist.py     Deterministic playlist operations
  search.py       Track search and metadata lookup
  track_refs.py   URI and URL normalization
  verify.py       Playlist order verification
tests/
examples/
```

## Development

```powershell
python -m pytest
python -m ruff check .
python -m mypy src
```

Spotify integration tests should stay opt-in and only run when `SPOTIFY_EXACT_RUN_INTEGRATION_TESTS=1` is set.

## Current Status

Implemented:

- deterministic input normalization for Spotify track URIs and track URLs
- ordered playlist creation and add operations with 100-item chunking
- validation before playlist writes
- playlist prefix verification
- read-only track search and track metadata lookup
- Rich table output and JSON output for search and track inspection
- mocked unit tests for playlist and search behavior

Still planned:

- integration tests against a real Spotify account
- richer error mapping for Spotify API failures
- YAML manifest creation
- playlist export, repair, and resolve workflows

## Determinism Policy

The playlist creation path accepts only Spotify track URIs and Spotify track URLs. Human-readable strings such as `Song Title by Artist` are rejected because resolving them would require search and manual review.
