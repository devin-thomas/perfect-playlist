# perfect-playlist

Deterministic Spotify playlist creation from exact track URIs.

`perfect-playlist` is a local CLI and importable Python package for creating Spotify playlists from an ordered list of exact Spotify track URIs or track URLs. It does not search, substitute, reorder, or silently skip tracks during playlist creation.

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
perfect-playlist playlist create "The Paradox Tiny Desk - Available Tracks" --private --from examples/paradox-tiny-desk.txt --dry-run
```

Create the playlist:

```powershell
perfect-playlist playlist create "The Paradox Tiny Desk - Available Tracks" --private --from examples/paradox-tiny-desk.txt --verify
```

Create from a strict YAML manifest:

```powershell
perfect-playlist playlist create --manifest examples/paradox-tiny-desk.yaml --dry-run
```

Manifest entries must contain an exact Spotify track URI or URL. Entries marked
`missing: true` are excluded from the write while preserving the order of all
verified tracks; any other entry without a URI fails validation.

## CLI Shape

```text
perfect-playlist
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
from perfect_playlist import create_playlist_from_uris

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
src/perfect_playlist/
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

Spotify integration tests should stay opt-in and only run when `PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1` is set.

## Spotify Integration Validation

The default test suite does not contact Spotify. To run the real integration check, configure a local `.env` with:

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

Then run:

```powershell
$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS="1"
python -m pytest tests/integration
```

The integration test creates a private playlist named `perfect-playlist integration test - DELETE ME - <timestamp>` and verifies that the Spotify track order matches `examples/paradox-tiny-desk.txt`.

## Current Status

Implemented:

- deterministic input normalization for Spotify track URIs and track URLs
- ordered playlist creation and add operations with 100-item chunking
- validation before playlist writes
- playlist prefix verification
- read-only track search and track metadata lookup
- typed Spotify auth and API error handling
- Rich table output and JSON output for search and track inspection
- mocked unit tests for playlist and search behavior

Still planned:

- a credentialed run of the opt-in Spotify integration test
- playlist repair and resolve workflows

Export an existing playlist to an exact URI file:

```powershell
perfect-playlist playlist export PLAYLIST_ID --out playlist.txt
```

## Determinism Policy

The playlist creation path accepts only Spotify track URIs and Spotify track URLs. Human-readable strings such as `Song Title by Artist` are rejected because resolving them would require search and manual review.
