# Perfect Playlist Playlist CLI — Build Plan

## Goal

Build a local Spotify CLI and reusable Python package that creates playlists from **exact Spotify track URIs in exact order**, with no generative substitution, no fuzzy replacement, and no hidden reordering.

This is meant to solve the failure mode we hit with the ChatGPT Spotify connector: it can describe a playlist to Spotify, but it does not appear to expose deterministic playlist construction from exact track IDs. Our tool should use the Spotify Web API directly.

## Non-goals

This project should **not** try to be a general music recommendation engine.

It should also avoid these behaviors by default:

- Automatically substituting a “close enough” song.
- Reordering tracks for vibe, popularity, release order, or recommendation quality.
- Silently skipping missing tracks.
- Creating a playlist from title strings unless the user explicitly accepts the resolved track IDs.
- Depending on an LLM or generative playlist layer for the final write operation.

## Core principle

The CLI should be **library-first**.

The command-line interface is only a thin wrapper over importable Python functions. That makes the same code easy to use from:

- shell scripts
- Python scripts
- future web apps
- future local tools
- future ChatGPT/Codex workflows
- scheduled jobs
- test suites

## Spotify API facts this plan relies on

Spotify’s Web API can create an empty playlist for the current user via `POST /me/playlists`. Private playlist creation requires the `playlist-modify-private` scope.

Spotify’s playlist add-items endpoint accepts Spotify URIs and adds items in the order provided. It also limits each add request to 100 items, so the package should chunk larger playlists into batches of 100.

Spotify requires registered redirect URIs for OAuth flows. For local desktop/CLI use, Spotify’s current redirect URI rules allow loopback IP literals such as `http://127.0.0.1:8000/callback`; `localhost` should not be used for newly validated apps.

Spotipy is a lightweight Python wrapper around the Spotify Web API and includes user authorization support plus playlist helper methods such as `playlist_add_items()`.

Reference links are collected at the bottom of this file.

---

# Recommended stack

## Language

Use **Python 3.11+**.

Python is a good fit because:

- Spotify automation libraries already exist.
- It is easy to package as both a CLI and importable module.
- It is easy to script from other programs.
- It is familiar enough for quick one-off use.

## Dependency choices

Recommended MVP dependencies:

```toml
spotipy = ">=2.25"
python-dotenv = ">=1.0"
typer = ">=0.12"
rich = ">=13.0"
pydantic = ">=2.0"
platformdirs = ">=4.0"
```

Reasoning:

- `spotipy`: handles Spotify OAuth and API calls.
- `python-dotenv`: loads local `.env` config during development.
- `typer`: clean CLI with type hints.
- `rich`: readable tables and error output.
- `pydantic`: validates manifests and internal models.
- `platformdirs`: stores token/cache/config files in OS-appropriate locations.

Potential later dependencies:

```toml
pytest = ">=8.0"
responses = ">=0.25"
ruff = ">=0.6"
mypy = ">=1.10"
pyyaml = ">=6.0"
```

`pyyaml` is optional. The MVP can support plain `.txt` files first, then YAML/JSON manifests later.

---

# User experience target

## Fast path: create a playlist from exact URIs

Input file:

```text
spotify:track:354WZaV3u6cuzTG2PmpYwm
spotify:track:78APbsosmvDYIwZHjzC5ZE
spotify:track:1OAMZ1AV5y6DHI5kzP0L3V
spotify:track:6FVeZfWkYtDiyyq93dBSXU
spotify:track:1y6lq1wrAspWEgRJmYb11S
```

Command:

```powershell
perfect-playlist playlist create "The Paradox Tiny Desk - Available Tracks" --private --from paradox.txt
```

Expected behavior:

1. Read the file top-to-bottom.
2. Normalize all Spotify URLs to `spotify:track:<id>` URIs if needed.
3. Validate that every line is a track URI.
4. Create an empty private playlist.
5. Add the tracks in exactly the input order.
6. Print the playlist URL.
7. Optionally verify the first N playlist items match the input order.

## Search flow: find exact track candidates

```powershell
perfect-playlist search track 'track:"Get The Message" artist:"The Paradox"' --limit 10
```

Output should show a table:

```text
#  Title              Artists                         Duration  Explicit  URI
1  Get The Message    The Paradox                     2:42      yes       spotify:track:354WZaV3u6cuzTG2PmpYwm
2  Get The Message    The Paradox                     2:42      no        spotify:track:5qWMTyC4l78azDudfo9bu0
```

The search command may be fuzzy because Spotify search itself is fuzzy. The playlist creation command should not be fuzzy.

## Dry run flow

```powershell
perfect-playlist playlist create "Test Playlist" --private --from paradox.txt --dry-run
```

Expected behavior:

- No Spotify write operation.
- Show normalized URIs.
- Optionally fetch metadata for each track.
- Report duplicates.
- Report invalid lines.
- Report the number of API calls that would be made.

---

# Package architecture

## Project layout

```text
perfect-playlist/
  README.md
  LICENSE
  pyproject.toml
  .gitignore
  .env.example
  src/
    perfect_playlist/
      __init__.py
      auth.py
      client.py
      cli.py
      config.py
      errors.py
      io.py
      models.py
      playlist.py
      search.py
      track_refs.py
      verify.py
  tests/
    test_track_refs.py
    test_io.py
    test_playlist_chunking.py
    test_manifest_validation.py
    test_cli_smoke.py
  examples/
    paradox-tiny-desk.txt
    paradox-tiny-desk.yaml
    create_paradox_playlist.py
```

## Module responsibilities

### `auth.py`

Responsible for OAuth and token cache setup.

Functions:

```python
def build_auth_manager(
    *,
    scope: str | None = None,
    cache_path: str | None = None,
    open_browser: bool = True,
) -> SpotifyOAuth:
    ...
```

Design notes:

- Use `SpotifyOAuth` from Spotipy for MVP.
- Default scope should include only what is needed:
  - `playlist-modify-private`
  - `playlist-modify-public`
  - `playlist-read-private` for verification and listing
- Store token cache outside the repo by default.
- Allow overriding via environment variables.

Suggested environment variables:

```env
SPOTIPY_CLIENT_ID=...
SPOTIPY_CLIENT_SECRET=...
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
PERFECT_PLAYLIST_TOKEN_CACHE=...
```

### `client.py`

Responsible for creating the Spotify API client.

Functions:

```python
def get_spotify_client() -> spotipy.Spotify:
    ...
```

Later, this module can hide the implementation choice so the package can switch from Spotipy to raw `httpx` without changing the public API.

### `models.py`

Responsible for typed return values.

Suggested dataclasses/Pydantic models:

```python
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
    warnings: list[str] = []
```

### `track_refs.py`

Responsible for accepting messy user input and normalizing it.

Functions:

```python
def normalize_track_ref(value: str) -> str:
    """Return spotify:track:<id> from a Spotify URI or open.spotify.com track URL."""


def is_track_uri(value: str) -> bool:
    ...


def extract_track_id(value: str) -> str:
    ...
```

Accepted inputs:

```text
spotify:track:354WZaV3u6cuzTG2PmpYwm
https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm
https://open.spotify.com/track/354WZaV3u6cuzTG2PmpYwm?si=abc123
```

Rejected inputs:

```text
spotify:album:...
spotify:playlist:...
https://youtube.com/...
Get The Message by The Paradox
```

Title strings should be rejected by `playlist create --from`, because accepting them would reintroduce nondeterminism.

### `io.py`

Responsible for reading input files.

Functions:

```python
def read_uri_lines(path: str | Path) -> list[str]:
    ...


def read_manifest(path: str | Path) -> PlaylistManifest:
    ...
```

Plain-text file rules:

- Blank lines ignored.
- Lines beginning with `#` ignored.
- Inline comments optionally supported later.
- Track URIs kept in original order.
- Duplicate URIs allowed by default because repeated songs may be intentional.

### `search.py`

Responsible for track search and metadata lookup.

Functions:

```python
def search_tracks(
    query: str,
    *,
    limit: int = 10,
    market: str | None = "US",
) -> list[TrackSummary]:
    ...


def get_tracks(
    uris: Sequence[str],
    *,
    market: str | None = "US",
) -> list[TrackSummary]:
    ...
```

Search rules:

- Search can be fuzzy.
- Search should never write to Spotify.
- Search output should include URIs so the user can copy exact matches into a playlist file.

### `playlist.py`

The most important module. It owns deterministic write operations.

Public functions:

```python
def create_empty_playlist(
    name: str,
    *,
    public: bool = False,
    description: str = "",
    collaborative: bool = False,
) -> CreatedPlaylist:
    ...


def add_items_in_order(
    playlist_id: str,
    uris: Sequence[str],
    *,
    start_position: int | None = None,
) -> str:
    """Add items in the exact order provided. Return the final snapshot_id."""


def create_playlist_from_uris(
    name: str,
    uris: Sequence[str],
    *,
    public: bool = False,
    description: str = "",
    dry_run: bool = False,
    verify: bool = True,
) -> PlaylistCreateResult:
    ...
```

Implementation notes:

- Validate every URI before creating the playlist.
- Chunk URI batches into groups of 100.
- Add chunks sequentially.
- Do not parallelize playlist writes, because ordering matters.
- If any add fails, raise an error that includes the playlist URL and the chunk index.
- Consider adding rollback support later, but do not silently delete partially created playlists in MVP.

### `verify.py`

Responsible for confirming that Spotify state matches local intent.

Functions:

```python
def get_playlist_track_uris(
    playlist_id: str,
    *,
    limit: int | None = None,
) -> list[str]:
    ...


def verify_playlist_prefix(
    playlist_id: str,
    expected_uris: Sequence[str],
) -> bool:
    ...
```

Verification behavior:

- Fetch playlist items after creation.
- Compare actual URI order to expected URI order.
- Report mismatches by index.
- Do not attempt to “fix” mismatches automatically unless a separate `repair` command is implemented.

### `errors.py`

Centralize custom exceptions.

Suggested exceptions:

```python
class SpotifyExactError(Exception): ...
class InvalidTrackRefError(SpotifyExactError): ...
class PlaylistCreateError(SpotifyExactError): ...
class PlaylistAddError(SpotifyExactError): ...
class PlaylistVerificationError(SpotifyExactError): ...
class AuthConfigError(SpotifyExactError): ...
```

The CLI can catch these and show friendly messages while the package still exposes useful errors to calling programs.

### `cli.py`

Thin Typer wrapper.

Suggested command tree:

```text
perfect-playlist
  auth
    login
    status
    logout
  search
    track QUERY
  track
    show URI_OR_URL
  playlist
    create NAME --from FILE [--private/--public] [--dry-run] [--verify]
    add PLAYLIST_ID --from FILE [--position N]
    verify PLAYLIST_ID --from FILE
    show PLAYLIST_ID
```

Design rule:

The CLI should not contain business logic. It should call functions from `playlist.py`, `search.py`, `io.py`, and `verify.py`.

---

# Public API design

The package should be useful from Python with minimal ceremony.

## Example: create a playlist from exact URIs

```python
from perfect_playlist import create_playlist_from_uris

result = create_playlist_from_uris(
    name="The Paradox Tiny Desk - Available Tracks",
    uris=[
        "spotify:track:354WZaV3u6cuzTG2PmpYwm",
        "spotify:track:78APbsosmvDYIwZHjzC5ZE",
        "spotify:track:1OAMZ1AV5y6DHI5kzP0L3V",
        "spotify:track:6FVeZfWkYtDiyyq93dBSXU",
        "spotify:track:1y6lq1wrAspWEgRJmYb11S",
    ],
    public=False,
    verify=True,
)

print(result.playlist.url)
```

## Example: search and manually choose

```python
from perfect_playlist import search_tracks

matches = search_tracks('track:"I Kinda Like That" artist:"The Paradox"')
for match in matches:
    print(match.title, match.artists, match.uri)
```

## Example: create from a file

```python
from perfect_playlist import create_playlist_from_file

result = create_playlist_from_file(
    name="Setlist",
    path="setlist.txt",
    public=False,
)
```

## Package exports

`src/perfect_playlist/__init__.py` should export a carefully chosen API:

```python
from .playlist import (
    create_empty_playlist,
    add_items_in_order,
    create_playlist_from_uris,
    create_playlist_from_file,
)
from .search import search_tracks, get_tracks
from .track_refs import normalize_track_ref, is_track_uri, extract_track_id
from .verify import verify_playlist_prefix
from .models import TrackSummary, CreatedPlaylist, PlaylistCreateResult
```

Avoid exporting Spotipy internals from the top-level package. Keep that dependency swappable.

---

# Manifest formats

## MVP: plain text

Use `.txt` first because it is hard to mess up.

```text
# The Paradox Tiny Desk - Available Tracks
spotify:track:354WZaV3u6cuzTG2PmpYwm
spotify:track:78APbsosmvDYIwZHjzC5ZE
spotify:track:1OAMZ1AV5y6DHI5kzP0L3V
spotify:track:6FVeZfWkYtDiyyq93dBSXU
spotify:track:1y6lq1wrAspWEgRJmYb11S
```

## Later: YAML manifest

YAML is useful when you want human-readable notes for missing songs.

```yaml
name: The Paradox Tiny Desk
public: false
description: Exact available Spotify tracks from the Tiny Desk setlist.
tracks:
  - title: Get The Message
    artist: The Paradox
    uri: spotify:track:354WZaV3u6cuzTG2PmpYwm
  - title: Bender
    artist: The Paradox, Travis Barker
    uri: spotify:track:78APbsosmvDYIwZHjzC5ZE
  - title: Good For Me
    artist: The Paradox
    uri: spotify:track:1OAMZ1AV5y6DHI5kzP0L3V
  - title: I Kinda Like That
    artist: The Paradox
    missing: true
    note: Exact Spotify track not verified.
  - title: Ms. Lauren
    artist: The Paradox
    uri: spotify:track:6FVeZfWkYtDiyyq93dBSXU
  - title: Do Me Like That
    artist: The Paradox
    uri: spotify:track:1y6lq1wrAspWEgRJmYb11S
```

Default YAML behavior should be strict:

- Entries with `missing: true` are not added.
- Entries without `uri` and without `missing: true` are validation errors.
- A command flag like `--fail-on-missing` can make missing entries block creation.

---

# CLI command details

## `auth login`

```powershell
perfect-playlist auth login
```

Expected behavior:

- Loads env vars.
- Opens browser for Spotify OAuth.
- Stores token cache.
- Prints authenticated user display name and account ID.

## `auth status`

```powershell
perfect-playlist auth status
```

Expected behavior:

- Confirms whether a cached token exists.
- Calls `me()` to show the active Spotify user.
- Does not expose access tokens.

## `search track`

```powershell
perfect-playlist search track 'track:"Get The Message" artist:"The Paradox"' --market US --limit 10
```

Expected behavior:

- Prints top results with title, artists, duration, explicit flag, URI, and URL.
- Optionally supports `--json` for scripts.

## `track show`

```powershell
perfect-playlist track show spotify:track:354WZaV3u6cuzTG2PmpYwm
```

Expected behavior:

- Normalizes URI/URL.
- Fetches metadata.
- Prints one track summary.

## `playlist create`

```powershell
perfect-playlist playlist create "Playlist Name" --from tracks.txt --private --verify
```

Expected behavior:

- Fails before writing if input validation fails.
- Creates empty playlist.
- Adds track URIs sequentially in chunks.
- Verifies order if requested.
- Prints playlist URL.

## `playlist add`

```powershell
perfect-playlist playlist add 3cEYpjA9oz9GiPac4AsH4n --from tracks.txt --position 0
```

Expected behavior:

- Adds tracks to an existing playlist.
- Supports optional zero-based insert position.
- Does not create a new playlist.

## `playlist verify`

```powershell
perfect-playlist playlist verify 3cEYpjA9oz9GiPac4AsH4n --from tracks.txt
```

Expected behavior:

- Fetches playlist items.
- Compares against input file.
- Prints first mismatch or success.
- Exits with nonzero status on mismatch.

---

# Packaging plan

## `pyproject.toml`

Use modern Python packaging.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "perfect-playlist"
version = "0.1.0"
description = "Deterministic Spotify playlist creation from exact track URIs."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
  { name = "Devin Thomas" }
]
dependencies = [
  "spotipy>=2.25",
  "python-dotenv>=1.0",
  "typer>=0.12",
  "rich>=13.0",
  "pydantic>=2.0",
  "platformdirs>=4.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.6",
  "mypy>=1.10",
]
yaml = [
  "pyyaml>=6.0",
]

[project.scripts]
perfect-playlist = "perfect_playlist.cli:app"

[tool.ruff]
line-length = 100

[tool.mypy]
python_version = "3.11"
strict = true
```

## Install locally while developing

```powershell
cd C:\dev\perfect-playlist
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,yaml]"
```

## Install as a CLI with `pipx`

```powershell
pipx install C:\dev\perfect-playlist
```

## Run without installing globally

```powershell
python -m perfect_playlist.cli --help
```

---

# Configuration and secrets

## `.env.example`

```env
SPOTIPY_CLIENT_ID=your_client_id_here
SPOTIPY_CLIENT_SECRET=your_client_secret_here
SPOTIPY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

## `.gitignore`

```gitignore
.env
.spotify_token_cache
*.cache
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
dist/
build/
*.egg-info/
```

## Security rules

- Never commit `.env`.
- Never print tokens.
- Never include token cache files in examples.
- Prefer minimum scopes.
- For this tool, do not request playback, library, or profile scopes unless a feature needs them.

---

# Implementation milestones

## Milestone 1 — MVP deterministic playlist creation

Deliverables:

- `normalize_track_ref()`
- `read_uri_lines()`
- `create_empty_playlist()`
- `add_items_in_order()`
- `create_playlist_from_uris()`
- CLI command: `playlist create`
- `.env.example`
- Basic README setup instructions

Acceptance criteria:

- Given a five-line URI file, the CLI creates a playlist with exactly those five tracks in that order.
- Given an invalid URL, it fails before creating a playlist.
- Given 101 tracks, it sends two sequential add requests.

## Milestone 2 — Search and metadata lookup

Deliverables:

- `search_tracks()`
- `get_tracks()`
- CLI command: `search track`
- CLI command: `track show`
- Rich table output
- Optional `--json` output

Acceptance criteria:

- Search results expose copyable Spotify URIs.
- Search does not write to Spotify.
- JSON output can be piped into other tools.

## Milestone 3 — Verification

Deliverables:

- `get_playlist_track_uris()`
- `verify_playlist_prefix()`
- CLI command: `playlist verify`
- `--verify/--no-verify` option for playlist creation

Acceptance criteria:

- Verification passes for a freshly created playlist.
- Verification identifies first mismatch by index.
- CLI exits nonzero on verification failure.

## Milestone 4 — Importable package quality

Deliverables:

- Stable top-level API in `__init__.py`
- Typed models
- Custom exceptions
- Unit tests
- `pyproject.toml`
- `pipx` install path

Acceptance criteria:

- Another Python script can call `create_playlist_from_uris()` without invoking the CLI.
- Package can be installed with `pip install -e .`.
- Tests pass without hitting Spotify by mocking API calls.

## Milestone 5 — Manifests and convenience workflows

Deliverables:

- YAML manifest support
- CLI command: `playlist create --manifest file.yaml`
- Missing-track handling
- Export command for playlist to URI file

Acceptance criteria:

- YAML can include notes and missing tracks.
- Missing tracks are handled explicitly, not silently.
- A playlist can be exported and re-created deterministically.

---

# Testing strategy

## Unit tests

Test without Spotify network calls.

Important cases:

- Normalize `spotify:track:<id>`.
- Normalize `https://open.spotify.com/track/<id>?si=...`.
- Reject album, artist, playlist, and episode URIs in track-only mode.
- Preserve input order.
- Preserve duplicates.
- Ignore blank and comment lines.
- Chunk 100-item batches correctly.
- Raise before Spotify write on validation error.

## Mocked API tests

Mock Spotipy methods:

- `current_user()`
- `user_playlist_create()`
- `playlist_add_items()`
- `playlist_items()`
- `search()`
- `tracks()`

Verify:

- `playlist_add_items()` receives batches in expected order.
- `playlist_add_items()` is called sequentially.
- `position` is only passed when requested.
- errors include enough context to recover.

## Optional integration tests

Run only when credentials are present:

```powershell
$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS="1"
pytest tests/integration
```

Integration tests should create test playlists with obvious names like:

```text
perfect-playlist integration test - DELETE ME - 2026-06-30
```

They should not run by default.

---

# Error handling design

## Invalid input

Example:

```text
Line 4 is not a Spotify track URI or URL: I Kinda Like That - The Paradox
```

Exit code: `2`

## Auth failure

Example:

```text
Spotify auth failed. Check SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, and SPOTIPY_REDIRECT_URI.
```

Exit code: `3`

## Spotify API failure

Example:

```text
Spotify rejected add-items request for chunk 2/3. Playlist was created but may be incomplete:
https://open.spotify.com/playlist/...
```

Exit code: `4`

## Verification failure

Example:

```text
Playlist verification failed at index 3.
Expected: spotify:track:abc
Actual:   spotify:track:def
```

Exit code: `5`

---

# Rate limits and retries

Spotify can return `429 Too Many Requests`. The package should:

- Respect `Retry-After` when present.
- Use bounded retries for read operations.
- Be careful retrying write operations.
- If retrying a write after an ambiguous failure, re-fetch playlist state first when possible.

For MVP, keep writes simple:

1. Create playlist.
2. Add chunk.
3. If chunk call fails, stop and report partial state.
4. User can verify or repair manually.

---

# Determinism policy

## Strict mode: default

The default creation path accepts only exact track URIs/URLs.

```powershell
perfect-playlist playlist create "Name" --from tracks.txt
```

This path should never search.

## Resolve mode: optional later feature

A later command can help resolve human-readable setlists:

```powershell
perfect-playlist resolve setlist setlist.yaml --out resolved.yaml
```

But it should require review before creation.

Suggested flow:

1. Search candidates for each title/artist.
2. If exactly one high-confidence exact match exists, suggest it.
3. If ambiguous, mark `needs_review: true`.
4. User edits/approves the manifest.
5. `playlist create --manifest resolved.yaml` writes only approved URIs.

This keeps fuzzy search separate from deterministic writes.

---

# Example package usage from another program

## Simple function call

```python
from perfect_playlist import create_playlist_from_uris

uris = [
    "spotify:track:354WZaV3u6cuzTG2PmpYwm",
    "spotify:track:78APbsosmvDYIwZHjzC5ZE",
]

result = create_playlist_from_uris("My Exact Playlist", uris, public=False)
print(result.playlist.url)
```

## Use as part of a larger script

```python
from perfect_playlist import search_tracks, create_playlist_from_uris

queries = [
    'track:"Get The Message" artist:"The Paradox"',
    'track:"Bender" artist:"The Paradox"',
]

resolved = []
for query in queries:
    matches = search_tracks(query, limit=5)
    if len(matches) != 1:
        raise RuntimeError(f"Manual review needed for {query}: {matches}")
    resolved.append(matches[0].uri)

create_playlist_from_uris("Resolved Playlist", resolved, public=False)
```

## JSON output for non-Python programs

CLI commands should support `--json` so other languages can call the CLI.

```powershell
perfect-playlist search track 'track:"Bender" artist:"The Paradox"' --json
```

Possible output:

```json
[
  {
    "uri": "spotify:track:78APbsosmvDYIwZHjzC5ZE",
    "title": "Bender (feat. Travis Barker)",
    "artists": ["The Paradox", "Travis Barker"],
    "duration_ms": 170000,
    "url": "https://open.spotify.com/track/78APbsosmvDYIwZHjzC5ZE"
  }
]
```

---

# Future features

## Playlist repair

Command:

```powershell
perfect-playlist playlist repair PLAYLIST_ID --from tracks.txt
```

Possible strategies:

- Replace all playlist items with expected URI list.
- Reorder existing items.
- Insert missing items.
- Remove unexpected items.

This should be opt-in and dry-run by default.

## Export existing playlist

Command:

```powershell
perfect-playlist playlist export PLAYLIST_ID --out playlist.txt
```

Use cases:

- Backup playlist structure.
- Recreate playlist later.
- Compare playlist versions in Git.

## Local HTTP service

A tiny FastAPI wrapper could expose the package to other local tools:

```http
POST /playlists
{
  "name": "Setlist",
  "public": false,
  "uris": ["spotify:track:..."]
}
```

This is optional. The importable Python package and CLI should come first.

## Clipboard helper

Command:

```powershell
perfect-playlist playlist create "Clipboard Playlist" --from-clipboard
```

Useful for copying a block of Spotify links from notes.

## `uvx` / one-command execution

Later package publishing could allow:

```powershell
uvx perfect-playlist playlist create "Name" --from tracks.txt
```

---

# Development checklist

## Before coding

- [ ] Create Spotify developer app.
- [ ] Add redirect URI using `127.0.0.1`, not `localhost`.
- [ ] Create `.env` locally.
- [ ] Create repo in `C:\dev\perfect-playlist`.
- [ ] Add `.gitignore` before creating token cache.

## MVP coding order

1. `track_refs.py`
2. `io.py`
3. `auth.py`
4. `client.py`
5. `playlist.py`
6. `cli.py`
7. tests
8. README
9. examples

## First real-world test

Use this file:

```text
# The Paradox Tiny Desk - verified available tracks
spotify:track:354WZaV3u6cuzTG2PmpYwm
spotify:track:78APbsosmvDYIwZHjzC5ZE
spotify:track:1OAMZ1AV5y6DHI5kzP0L3V
spotify:track:6FVeZfWkYtDiyyq93dBSXU
spotify:track:1y6lq1wrAspWEgRJmYb11S
```

Run:

```powershell
perfect-playlist playlist create "The Paradox Tiny Desk - Available Tracks" --private --from examples/paradox-tiny-desk.txt --verify
```

Expected result:

- Five tracks added.
- Exact order preserved.
- Playlist URL printed.
- Verification passes.

---

# Rough MVP code sketch

This is not the full implementation, but it shows the intended separation between reusable functions and CLI.

```python
# src/perfect_playlist/playlist.py
from collections.abc import Sequence

from .client import get_spotify_client
from .track_refs import normalize_track_ref


def chunked(items: Sequence[str], size: int = 100):
    for i in range(0, len(items), size):
        yield list(items[i : i + size])


def create_playlist_from_uris(
    name: str,
    uris: Sequence[str],
    *,
    public: bool = False,
    description: str = "Created with perfect-playlist",
    dry_run: bool = False,
):
    normalized = [normalize_track_ref(uri) for uri in uris]

    if dry_run:
        return {
            "dry_run": True,
            "name": name,
            "public": public,
            "uris": normalized,
        }

    sp = get_spotify_client()
    user = sp.current_user()

    playlist = sp.user_playlist_create(
        user=user["id"],
        name=name,
        public=public,
        description=description,
    )

    snapshot_id = None
    for batch in chunked(normalized, 100):
        response = sp.playlist_add_items(playlist["id"], batch)
        snapshot_id = response.get("snapshot_id")

    return {
        "playlist_id": playlist["id"],
        "playlist_url": playlist["external_urls"]["spotify"],
        "snapshot_id": snapshot_id,
        "uris": normalized,
    }
```

```python
# src/perfect_playlist/cli.py
import typer
from rich import print

from .io import read_uri_lines
from .playlist import create_playlist_from_uris

app = typer.Typer()
playlist_app = typer.Typer()
app.add_typer(playlist_app, name="playlist")


@playlist_app.command("create")
def playlist_create(
    name: str,
    from_file: str = typer.Option(..., "--from", help="File of Spotify track URIs/URLs"),
    private: bool = typer.Option(False, "--private", help="Create a private playlist"),
    dry_run: bool = typer.Option(False, "--dry-run"),
):
    uris = read_uri_lines(from_file)
    result = create_playlist_from_uris(
        name=name,
        uris=uris,
        public=not private,
        dry_run=dry_run,
    )
    print(result)
```

---

# References

- Spotify Web API — Create Playlist: https://developer.spotify.com/documentation/web-api/reference/create-playlist
- Spotify Web API — Add Items to Playlist: https://developer.spotify.com/documentation/web-api/reference/add-tracks-to-playlist
- Spotify Web API — Redirect URIs: https://developer.spotify.com/documentation/web-api/concepts/redirect_uri
- Spotipy documentation: https://spotipy.readthedocs.io/en/2.25.1/

## Progress and Handoff

- 2026-07-10: The first unfinished product task, strict YAML manifest support,
  is complete. `read_manifest()` validates metadata and exact track references,
  excludes entries marked `missing: true`, and the CLI supports
  `playlist create --manifest FILE`.
- Verification completed: targeted manifest, CLI, and IO tests pass; full-suite
  verification passes with the opt-in integration test skipped.
- The opt-in Spotify integration test still requires local credentials and was
  intentionally not run against the external API.
- 2026-07-10: Playlist export is complete. `export_playlist_to_file()` writes
  the existing playlist's track URIs in Spotify order, and the CLI supports
  `playlist export PLAYLIST_ID --out FILE`.
- 2026-07-10: Playlist repair is complete. `repair_playlist()` previews by
  default and applies an exact replacement only with explicit opt-in; the CLI
  supports `playlist repair PLAYLIST_ID --from FILE [--apply]`.
- 2026-07-10: Resolve mode is complete. `resolve_setlist()` searches without
  writing to Spotify and emits a manifest with exact matches plus
  `needs_review: true` candidate entries; the CLI supports
  `resolve setlist INPUT --out OUTPUT`.
- 2026-07-10: Resolve review tooling now records a `0.0`-to-`1.0` confidence
  score for each candidate set while keeping ambiguous matches behind the
  `needs_review` gate.
