# Spotify Live QA Evidence and Handoff

Date: 2026-07-18
Repository: `C:\dev\personal\spotify-playlist-modify`
Branch: `main`

## Final M-27 Release Review

The independent final review traced the complete implementation and all 18 child-ticket acceptance criteria against `CLI-CONTRACT.md`. The review removed stale status text and dead compatibility code, tightened public-library Search and Inspect behavior, and added a fail-closed persisted-visibility check before a new public Build may add tracks.

Final validation uses the configured external Python 3.11 environment and temporary build/test directories outside the repository:

- `$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS='0'; python -m pytest --basetemp <external-temp>`: `133 passed, 2 skipped`; both skips are the explicitly opt-in live tests.
- `$env:PERFECT_PLAYLIST_RUN_INTEGRATION_TESTS='1'; python -m pytest --basetemp <external-temp>`: `135 passed, 0 skipped`.
- `python -m ruff check --no-cache perfect_playlist tests`: passed.
- `python -m mypy --no-incremental perfect_playlist tests`: passed with no issues in 29 source files.
- `python -m pip check`: no broken requirements.
- `python -m pip wheel . --no-deps --wheel-dir <external-temp>`: built `perfect_playlist-0.1.0-py3-none-any.whl` outside the repository.
- `python -m build --outdir <external-temp>`: built the source distribution and wheel outside the repository.
- `pwsh -NoProfile -File tests/Ralph.Core.Smoke.ps1`: passed.
- CLI help smoke: exposed only Build, Add, Verify, Export, Search, Inspect, and Auth.

The credentialed suite exercised and cleaned up new-public Build, owned empty public/private target Build, owned Add, live Verify, live Export round-trip, and partial/persisted-state safety. Timestamped `DELETE ME` public fixtures were unfollowed, and the reusable private target was restored to empty. No safe collaborative target was available, so collaborative Add remains covered by typed offline tests and no collaborative playlist was modified.

## Requested Five-Track Playlist

Discovery used serialized Search calls followed by Inspect for every selected canonical URI. The first-ranked original-album result was deliberately selected for Corey Lingo; the other four searches returned one exact candidate each.

| Order | Requested track | Inspected Spotify result | Canonical URI |
| ---: | --- | --- | --- |
| 1 | Corey Lingo - Call on You | Call On You - Corey Lingo, `For What It's Worth` | `spotify:track:5Qamlcya1Hz5Z4AgzdQ5q8` |
| 2 | goonie - gooey ft iayze | gooey - GOONIE, iayze | `spotify:track:5irdISp39LC6kD10muguYh` |
| 3 | $oFaygo - Rock Out | Rock Out! - SoFaygo | `spotify:track:6fNlPrHOIAtVLXHuBE23Vl` |
| 4 | Lil Shine - God | God - Lil Shine, `Shine Forever` | `spotify:track:2NpCynruGo9XeJPiq4SzB9` |
| 5 | Lil Gohan - Saints Row | Saints Row - Lil Gohan, `Dragon Rush 2` | `spotify:track:0w7x8ZkT6Yz1eKKKGz1CBG` |

The durable Source is `examples/final-review-sample.yaml`. Default Build created and verified [My Perfect Playlist](https://open.spotify.com/playlist/4t20ivHxAQtDiMnGINvsmL) with five tracks. A separate Verify command compared the local Source with the Spotify playlist and returned an exact five-track match. Spotify read-back reported:

- `public=true`
- `collaborative=false`
- description `Built with Perfect Playlist`
- total track count `5`

This playlist is the requested persistent user result, not a disposable integration fixture, so it was intentionally left in the test account.

## Authentication Note

The first parallel read-only discovery attempt encountered a transient Spotipy token-cache decode and authorization prompt. No playlist write had begun. `perfect-playlist auth login` refreshed the supported external cache successfully, after which serialized Search/Inspect calls, the full credentialed suite, Build, Verify, and metadata read-back all passed. Agents should serialize separate CLI processes that share the same OAuth cache.

## Spotify Privacy Behavior

Spotify has previously acknowledged a requested private creation in its immediate response and then reported the created playlist as public on read-back. Perfect Playlist therefore does not offer private creation as a Build workflow. It supports private Build only through an owned empty target that Spotify already reports as private. Creation and target writes re-read required persisted state and fail before adding tracks when Spotify does not satisfy the requested visibility.

## Safety and Cleanup

- `resources/spotify-secrets.env`, `.env` files, token caches, OAuth material, test caches, virtual environments, and build output remain ignored and untracked.
- The committed `spotify-secrets.env.example` contains only variable names used by the runtime, integration opt-in, or Ralph host setup.
- Generated wheels and final-review temporary directories were written outside the repository.
- The requested playlist URL and canonical Spotify track URIs are public identifiers and safe to retain as reproducible QA evidence.
