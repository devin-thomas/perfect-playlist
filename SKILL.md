# Perfect Playlist Agent Skill

Use Perfect Playlist as a deterministic final-mile tool. Discovery may be
intelligent, but playlist writes must receive the exact ordered Spotify track
references chosen by the caller.

## Before You Act

Read `docs/README.md`, `docs/CLI-CONTRACT.md`, and the relevant sections of
`docs/PRODUCT-AND-LANGUAGE.md`. Search the repository for existing examples and
tests before inventing a new shape. Use `search` and `inspect` to discover and
confirm candidates; neither command chooses tracks or writes a playlist.

## Durable Track Sequences

Create a local, reviewable Source containing only the selected tracks. YAML and
JSON use a top-level `tracks` array; text uses one track URI or URL per line.
Comments and blank lines are allowed only in text Sources. Preserve order and
duplicates. Pass execution details such as the playlist name, target, and
privacy as CLI options, never as fields in the TrackSequence.

```yaml
tracks:
  - spotify:track:354WZaV3u6cuzTG2PmpYwm
  - spotify:track:78APbsosmvDYIwZHjzC5ZE
```

Prefer canonical `spotify:track:<id>` URIs. Typed Spotify track URLs are also
accepted and normalized. Raw 22-character IDs, stdin (`-`), and remote YAML,
JSON, or text documents are invalid Sources. Invalid entries fail the complete
Source; never silently skip missing, ambiguous, or candidate-only entries.

## Deterministic Workflows

- `perfect-playlist search QUERY` returns track candidates. Use `--limit 1..10`
  when needed; the default is 4.
- `perfect-playlist inspect TRACK_URI_OR_URL` confirms one exact candidate.
- `perfect-playlist build SOURCE` creates a public playlist, using
  `--name NAME` for an explicit case-sensitive name or the default name when
  omitted. An explicit name collision fails; the default name gets a numeric
  suffix.
- `perfect-playlist build SOURCE --target PLAYLIST` fills an owned empty public
  or private target and preserves its metadata. `--private --target` requires
  Spotify to report that target as private. Interactive `--private` prompts for
  the target; non-interactive use requires `--target`.
- `perfect-playlist add SOURCE --target PLAYLIST` is append-only. It accepts a
  writable owned or collaborative playlist, never changes visibility, and
  verifies both the count increase and appended segment.
- `perfect-playlist verify LEFT RIGHT` treats both Sources as peers. Exit code
  0 means exact equality, exit code 1 means a count or positional mismatch,
  and exit code 2 means an invalid, inaccessible, or unauthenticated Source.
- `perfect-playlist export SOURCE` prints a text representation. Use
  `--out` for a new `.yaml`, `.yml`, `.json`, or `.txt` file and `--links` for
  text-only Spotify web links. Existing files are never overwritten.

Successful Build and Add operations validate before writing and read back what
Spotify stored. There is no dry run, repair, resolve, positional insertion,
overwrite, generative substitution, or compatibility alias.

## Authentication and Safety

Use `perfect-playlist auth login` for interactive authorization and
`perfect-playlist auth status` for a non-interactive check. Runtime credentials
belong only in the gitignored `resources/spotify-secrets.env`; use
`spotify-secrets.env.example` to learn variable names. Never open, print, copy,
modify, commit, or paste secrets, token caches, OAuth codes, or private values.

Surface handled failures clearly and preserve their exit code. Do not catch
broad exceptions, turn failures into success-shaped output, or claim a write
succeeded without post-write verification.

## Task Reporting

For repository implementation work, read `AGENTS.md` and the applicable task
execution prompt. Record start and end timestamps in America/Chicago and total
whole minutes. Run focused checks first, then every applicable repository check.
Report failures and skipped tests boldly and clearly; do not claim completion
when required validation is missing. Before marking a task complete, stage only
task-owned paths, inspect the cached diff, create a non-empty task commit, and
report the commit subject and SHA.
