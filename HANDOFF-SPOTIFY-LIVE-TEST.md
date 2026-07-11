# Spotify Live Test Handoff

Date: 2026-07-11
Repository: `C:\dev\personal\spotify-playlist-modify`
Branch: `main`

## Objective

Run a real Spotify integration test using these tracks, preserving order and
choosing explicit variants whenever Spotify exposes both explicit and clean
versions:

1. N.E.R.D. - Tape You
2. Snoop Dogg - Let's Get Blown
3. Pharrell - Frontin'
4. Snoop Dogg - Beautiful
5. Snoop Dogg - Peaches N Cream
6. Usher - U Don't Have to Call

## Completed Repository Work

The local package is implemented and verified through commit `700a677`:

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
- `python -m ruff check --no-cache src tests`: passed.
- `python -m mypy src`: passed with no issues in 14 source files.

The remote is configured as `origin` pointing to the expected GitHub
repository. The branch is currently ahead of `origin/main` by eight commits;
the requested cleanup and push have not happened yet.

## Live Search Results

Client-credential searches succeeded using the app credentials from
`resources/secrets.md`. The selected URIs were:

| Requested track | Selected variant | URI |
| --- | --- | --- |
| Tape You | N.E.R.D., explicit | `spotify:track:3REnVcPtMXDxR4g8sZ4QtM` |
| Let's Get Blown | Snoop Dogg, explicit | `spotify:track:0NdxbFFknA7kQ4E2zvJfey` |
| Frontin' | Club Mix, explicit | `spotify:track:0iFOG4Ki9aDmJUYUFHQlPG` |
| Beautiful | Snoop Dogg / Pharrell / Charlie Wilson, explicit | `spotify:track:7FrJV8tydWEv1Mxu2mIQrm` |
| Peaches N Cream | Clean; no explicit result was returned | `spotify:track:4lcpWCMFXNhvqNIQhB6yDv` |
| U Don't Have to Call | Usher, explicit | `spotify:track:5PCJldueshnwqQVjS16543` |

No playlist was created yet.

## Current Blocker

Spotify user OAuth is not complete in the Codex environment. App credentials
are present, but user-specific playlist scopes require an interactive account
authorization and a callback listener.

The registered redirect URI is the loopback root:

`http://127.0.0.1:4202`

There is intentionally no `/callback` suffix. Spotify requires the redirect
URI in the dashboard, authorization URL, and local configuration to match
exactly. `localhost` is no longer accepted by Spotify.

## Authorization Attempts

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

## Recommended Next Steps

1. Start the callback listener from the same normal host environment that runs
   the authenticated Chrome session, not from the restricted Codex sandbox.
   It must bind to `127.0.0.1:4202` before opening the Spotify authorization
   URL.
2. Reuse the exact redirect URI `http://127.0.0.1:4202` everywhere.
3. If using a manual callback helper, have it exchange the one-time `code`
   immediately and save the token outside the repository, for example under
   the platform cache directory used by `perfect-playlist`.
4. After OAuth succeeds, create a temporary private playlist using the six
   URIs above and verify the exact order with
   `verify_playlist_prefix()`.
5. Remove the temporary playlist manually after verification, or retain its
   URL for cleanup confirmation.
6. Run the full local checks again, inspect the diff for generated files or
   secrets, commit the cleanup, and push `main` to `origin`.

## Important Safety Notes

- Never commit `resources/secrets.md`, `.env`, token caches, authorization
  codes, client secrets, or access tokens.
- The six selected URIs are public Spotify identifiers and are safe to keep in
  a temporary local fixture, but the fixture should not replace the existing
  example unless that change is intentional.
- Do not claim the live integration passed until playlist creation and exact
  order verification both succeed against Spotify.
