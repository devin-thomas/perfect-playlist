# Spotify Live QA Evidence and Handoff

Date: 2026-07-13
Repository: `C:\dev\personal\spotify-playlist-modify`
Branch: `main`

Current checkpoint: Parent 1 is complete and Parent 2 is in progress through
owned empty-target Build. The canonical TrackSequence, Source pipeline,
authentication behavior, and top-level command shell are present. Parent 2
command `add` now has its append-only implementation. Parent 2 commands
`verify` and `export`, plus Parent 3 commands (`search` and `inspect`), fail
closed with exit code `2`; they do not write playlists or files or claim
verification.

The authoritative behavior is in `CLI-CONTRACT.md`; the ordered work and
current boundary are in `IMPLEMENTATION-PLAN.md`.

This document preserves historical live-test evidence. Legacy command names
and features mentioned in the chronology describe the implementation at the
time of testing and are not requirements for the next CLI.

## Current Parent 1 Verification

On 2026-07-13, the recovered Parent 1 checkpoint passed the publish gate in a
clean external Python 3.11 virtual environment:

- `python -m pip check`: no broken requirements.
- Package and CLI import smoke checks: passed.
- `python -m ruff check --no-cache perfect_playlist tests`: passed.
- `python -m mypy --no-incremental perfect_playlist tests`: passed with no
  issues in 23 source files.
- Offline pytest with `PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=0`: 70 passed,
  1 skipped. The one skip was the deliberately disabled credentialed Spotify
  integration test.
- Wheel build: passed for `perfect_playlist-0.1.0-py3-none-any.whl`; the wheel
  was written outside the repository.
- Credentialed pytest with `PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1`: 71
  passed, 0 skipped. The live test created a temporary public playlist, read
  back the exact track order and public visibility, and unfollowed the fixture
  in cleanup.

## Historical Always-On Baseline

On 2026-07-12, the local secrets file set
`PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1`. The full suite reported `41 passed`
with no skip: the live test created a temporary public playlist, added the
ordered example tracks, verified the result, confirmed persisted public
visibility, and unfollowed the fixture during cleanup. Repository-local pytest
temp paths prevent host/sandbox permission differences from blocking unrelated
tests.

## Historical Objective and Spotify Privacy Persistence Blocker

Run a real Spotify integration test using these tracks, preserving order and
choosing explicit variants whenever Spotify exposes both explicit and clean
versions:

1. N.E.R.D. - Tape You
2. Snoop Dogg - Let's Get Blown
3. Pharrell - Frontin'
4. Snoop Dogg - Beautiful
5. Snoop Dogg - Peaches N Cream
6. Usher - U Don't Have to Call

## Historical Pre-Parent 1 Repository State

Before the Parent 1 reconciliation, the package was implemented and verified
through commit `700a677` with these legacy capabilities:

- Exact URI and URL normalization.
- Deterministic playlist creation with validation-before-write.
- Ordered 100-item batching and verification.
- YAML manifests with strict validation and missing-track handling.
- Search-only setlist resolution with confidence scores and review gating.
- JSON output for resolver results.
- Playlist export and opt-in repair workflows.
- Reproducible Mypy configuration and PyYAML type stubs.

Latest local checks before the live-test attempt:

- `python -m pytest`: `37 passed, 1 skipped`.
- `python -m ruff check --no-cache perfect_playlist tests`: passed.
- `python -m mypy perfect_playlist`: passed with no issues in 14 source files.

The remote is configured as `origin` pointing to the expected GitHub
repository. Current publication state is verified from Git rather than this
historical snapshot.

## Live Search Results

Client-credential searches succeeded using the private app credentials now
stored in `resources/spotify-secrets.env`. The selected URIs were:

| Requested track | Selected variant | URI |
| --- | --- | --- |
| Tape You | N.E.R.D., explicit | `spotify:track:3REnVcPtMXDxR4g8sZ4QtM` |
| Let's Get Blown | Snoop Dogg, explicit | `spotify:track:0NdxbFFknA7kQ4E2zvJfey` |
| Frontin' | Club Mix, explicit | `spotify:track:0iFOG4Ki9aDmJUYUFHQlPG` |
| Beautiful | Snoop Dogg / Pharrell / Charlie Wilson, explicit | `spotify:track:7FrJV8tydWEv1Mxu2mIQrm` |
| Peaches N Cream | Clean; no explicit result was returned | `spotify:track:4lcpWCMFXNhvqNIQhB6yDv` |
| U Don't Have to Call | Usher, explicit | `spotify:track:5PCJldueshnwqQVjS16543` |

The six-track QA playlist was created and verified in exact order and currently
reports `public=false`:

`https://open.spotify.com/playlist/1wZZhNXDthlPBXtreCMyCA`

## OAuth Resolution

Spotify user OAuth completed successfully by running Spotipy's built-in
loopback listener and browser launch from the same host environment. The
callback used the registered loopback root exactly:

The registered redirect URI is the loopback root:

`http://127.0.0.1:4202`

There is intentionally no `/callback` suffix. The redirect URI in the Spotify
dashboard, authorization URL, and local configuration matched exactly.

The successful authorization exposed a package defect: Spotipy could obtain a
token but could not save it because the platform token-cache parent directory
did not exist. `build_auth_manager()` now creates that directory before
constructing the cache handler. Playlist creation was also migrated from the
deprecated `user_playlist_create()` helper to
`current_user_playlist_create()`.

## Authorization and Privacy Findings

1. The original `http://localhost:4202` redirect was rejected by Spotify as an
   insecure redirect URI.
2. The Spotify app dashboard was updated to `http://127.0.0.1:4202`.
3. The local secrets file was updated to use the same loopback URI.
4. A corrected authorization URL was generated with the required playlist
   scopes.
5. Authorization succeeded in the user's authenticated Chrome session, but
   Chrome returned to `127.0.0.1:4202` with `ERR_CONNECTION_REFUSED` because no
   callback listener was reachable at that moment.
6. Temporary callback listeners were started from the Codex environment and
   the redirect page was reloaded, but the separate Chrome session continued
   to receive connection refused.
7. No client secret, access token, refresh token, or authorization code was
   written to this document or committed.
8. The host-level OAuth flow authenticated the active Spotify account and the
   corrected package persisted its token outside the repository.
9. The six-track QA playlist was created and read back successfully;
   exact-order verification returned `True`.
10. A later opt-in integration playlist requested `public=false` but persisted
    as `public=true`; the original test missed this because it asserted only
    the URL and track order.
11. Isolated create probes proved Spotipy sent the correct Boolean value and
    the token contained `playlist-modify-private`. Spotify's create response
    said `public=false`, but follow-up reads returned `public=true`.
12. Spotify's documented change-details request also returned success without
    changing the persisted public state.
13. The package now re-reads persisted visibility and aborts before adding
    tracks if a requested private playlist is public.

## Historical Verification

- `python -m pytest`: `39 passed, 1 skipped`; the skipped test is the explicitly
  opt-in live Spotify integration test.
- Full credentialed run with `PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS=1`:
  `39 passed, 1 failed, 0 skipped`. The single failure is persisted privacy;
  Spotify returned `public=true`, and the package aborted with zero tracks
  added.
- `python -m ruff check --no-cache perfect_playlist tests`: passed.
- `python -m mypy perfect_playlist`: passed with no issues in 14 source files.
- Six-track final QA playlist: 6 tracks added, exact order verified.
- The accidentally public five-track integration fixture was emptied and
  unfollowed.

## Historical External Cleanup

1. Delete the final QA playlist linked above when it is no longer needed as
   release evidence.
2. Do not ship private creation as passing until a live create persists
   `public=false` and the full credentialed suite reports zero failures.

Parent 2 implementation is in progress; append-only Add is the latest
completed workflow checkpoint.

## Important Safety Notes

- Never commit `resources/spotify-secrets.env`, `.env`, token caches, authorization
  codes, client secrets, or access tokens.
- The six selected URIs are public Spotify identifiers and are safe to keep in
  a temporary local fixture, but the fixture should not replace the existing
  example unless that change is intentional.
- Spotify documents that Web API `public=false` removes a playlist from profile
  and search but is not access control; true link privacy requires a Spotify
  client.
- Do not claim the live integration passed until persisted visibility, playlist
  creation, and exact-order verification all succeed against Spotify.
