# CLI Contract

This document is the authoritative product and behavior contract for the next Perfect Playlist CLI. The implementation plan derives from it; code, tests, tutorials, agent guidance, and command examples must agree with it.

**Status:** Approved and ready for implementation.

See [Product and Language](PRODUCT-AND-LANGUAGE.md) for the vision, origin, principles, and canonical terms.

The primary consumer is expected to be an AI agent using project-provided `SKILL.md` and `AGENTS.md` guidance. The CLI remains understandable to humans, but its central purpose is to provide a deterministic Spotify write primitive instead of sending a natural-language prompt into another generative playlist layer.

## Command Language

Commands are actions, not object namespaces. `playlist` is implicit in the product name and does not appear as a command group.

```text
perfect-playlist build
perfect-playlist add
perfect-playlist verify
perfect-playlist export
perfect-playlist search
perfect-playlist inspect
perfect-playlist auth login
perfect-playlist auth status
```

`repair` is not part of the shipped interface because no command should overwrite a non-empty playlist. `resolve` is not part of the interface because unresolved candidates require a second data model outside TrackSequence.

The action-based CLI replaces all legacy grouped commands in one breaking release. There are no aliases, compatibility shims, or transitional warnings. Documentation, examples, tests, and future `SKILL.md`/`AGENTS.md` guidance use only the new commands.

## TrackSequence and Sources

`TrackSequence` is the common ordered representation used by `build`, `add`, `verify`, and `export`. It contains canonical Spotify track URIs, preserves duplicates, and contains no descriptive metadata.

A Source is auto-detected and resolves to a TrackSequence. Supported Sources are YAML, JSON, and plain-text files; Spotify playlist URLs and URIs; and individual Spotify track URLs and URIs.

Stdin is not a Source. The CLI does not accept `-`; Source input must remain durable and reproducible.

Raw 22-character Spotify IDs are rejected everywhere, including `--target`. Spotify references must be typed `spotify:` URIs or `open.spotify.com` links.

Arbitrary remote YAML, JSON, and text URLs are rejected. The error instructs the caller to download the document locally and pass the resulting file. Spotify links remain valid remote Sources because they identify Spotify resources read through Spotify's API.

Local Source files are parsed by extension with no content sniffing:

- `.yaml` and `.yml` parse a YAML object containing `tracks`.
- `.json` parses a JSON object containing `tracks`.
- `.txt` parses one Spotify track URI or link per nonblank line and permits `#` comments.
- Missing or unknown extensions exit `2` and list the supported extensions.
- Malformed content exits `2` with the filename and specific parse or validation error.

TrackSequence is the only portable playlist data type.

- YAML and JSON use only the top-level `tracks` array.
- Extra top-level YAML/JSON fields are ignored.
- Each `tracks` entry may be a Spotify track URI/link string or an object containing `uri`.
- A track object's `uri` may itself contain a Spotify track URI or link; all other object keys are ignored.
- Missing or invalid `uri` values fail the entire Source. `missing`, `needs_review`, and candidate-only entries are never silently skipped.
- Export always emits the canonical string-array form.
- Name, target, privacy choice, and other execution details are CLI flags or Python arguments, never TrackSequence fields.
- `BuildSpec`, `PerfectPlaylist`, and other wrapper schemas are not part of the model.
- A target cannot be embedded in YAML/JSON; AI agents and automation pass `--target`.

## Build

`build` is the primary product action.

```text
perfect-playlist build SOURCE --name "Road Trip"
perfect-playlist build SOURCE --target PLAYLIST
perfect-playlist build SOURCE --private
```

- With no target, build creates a new public playlist.
- With an owned empty public or private target, build fills that target.
- A private build requires an owned empty target.
- Collaborative playlists cannot be build targets.
- `--name` and `--target` are mutually exclusive.
- `--name` is public creation only.
- `--target` accepts an owned empty public or private playlist and preserves its existing Spotify name.
- `--private` without `--target` is available only in an interactive terminal and prompts for the private playlist link.
- Non-interactive private mode requires `--target`.
- `--private --target PLAYLIST` is the non-interactive private form and requires Spotify to report that target as private before writing.
- `--target PLAYLIST` without `--private` accepts either an owned empty public or private target.
- `--private` and `--name` are mutually exclusive.
- With neither `--name` nor `--target`, public creation uses `My Perfect Playlist`.
- If the default name is taken, advance through `My Perfect Playlist (1)`, `My Perfect Playlist (2)`, and so on.
- An explicit `--name` is never changed. If it is taken, exit `2` before creation.
- A name is taken only when the signed-in user owns a playlist with the exact case-sensitive name.
- Owned public and private playlists count. Followed and collaborator-owned playlists do not.
- If the owned-playlist scan cannot complete, fail before creation rather than guessing that a name is available.
- Every newly created public playlist uses the exact description `Built with Perfect Playlist`.
- Build has no description option, and TrackSequence YAML/JSON contains no description field.
- Target builds preserve the target playlist's existing name and description.
- Build rejects an empty TrackSequence with exit `2` before any Spotify write.
- Success prints `Built and verified "{name}" with {n} tracks: {url}` and exits `0`.

## Add

`add` is a secondary, append-only action.

```text
perfect-playlist add SOURCE --target PLAYLIST
```

- It may append to any playlist Spotify permits the signed-in user to modify.
- Owned and collaborative playlists are accepted.
- Public and private playlists are accepted.
- It never changes visibility and never inserts, prepends, or overwrites.
- `--target` is always required; add never prompts for a target.
- Before writing, record the target count.
- After writing, require the count to increase by exactly the Source length and require the appended segment to equal the Source TrackSequence.
- Add does not verify or make claims about the target's earlier contents.
- Concurrent target changes produce a handled operational failure rather than success.
- Add rejects an empty TrackSequence with exit `2` before reading or writing the target.
- Success prints `Added and verified {n} tracks in "{name}": {url}` and exits `0`.

Build and Add do not provide `--dry-run`. Search, Inspect, Export, and Verify cover read-only inspection, while write actions validate before writing and verify afterward.

## Verify

```text
perfect-playlist verify LEFT RIGHT
```

Both Sources are peers. Verification ignores ownership and compares only their TrackSequences.

- Exact equality prints `Verified: both sources contain {n} tracks and they all match.` and exits `0`.
- If counts differ, print only the two counts and exit `1`.
- If counts match but content differs, print only the first differing position and exit `1`.
- Display positions are one-based.
- File Sources are labeled with their filename; Spotify Sources and single-track Sources are labeled with their canonical URI.
- Count mismatch output is `Not verified: track counts differ.` followed by the two labeled counts.
- Positional mismatch output is `Not verified at position N.` followed by the two labeled URIs.
- Invalid, inaccessible, unauthenticated, or malformed Sources receive a clear handled error and exit `2`.
- Prefix-only verification and full diff output are not included.
- Empty-to-empty Sources may be Verified. Empty versus non-empty exits `1` through the count rule.

## Export

```text
perfect-playlist export SOURCE
perfect-playlist export SOURCE --out playlist.yaml
perfect-playlist export SOURCE --links
perfect-playlist export SOURCE --links --out playlist_links.txt
```

- Normal output renders canonical URI lines to stdout.
- `--links` renders `open.spotify.com` track links to stdout and is text-only.
- `.yaml` and `.yml` serialize the TrackSequence as YAML.
- `.json` serializes the TrackSequence as JSON.
- `.txt` writes one canonical URI per line, or one link per line with `--links`.
- An unknown or missing output extension exits `2` and lists the supported extensions.
- Export has no generic `--format` option; the output extension selects serialization.
- When `--out` is omitted in an interactive terminal, print the lines and then prompt to save.
- Normal output prompts `Save as YAML? [Y/n]`.
- Link output prompts `Save links as text? [Y/n]`.
- Pressing Enter saves.
- The suggested names are `playlist.yaml` and `playlist_links.txt`.
- Interactive implicit saves never overwrite. Existing names advance as `playlist.yaml`, `playlist(1).yaml`, `playlist(2).yaml`, and so on; link names advance as `playlist_links.txt`, `playlist_links(1).txt`, and so on.
- An explicit `--out` path is exact. If it already exists, exit `2` with `File already exists`.
- Export has no force or overwrite option.
- With explicit `--out`, do not print the TrackSequence; print one confirmation line such as `Exported 12 tracks to playlist.yaml.` or `Exported 12 links to playlist_links.txt.`
- After an interactive implicit save, the confirmation reports the actual collision-free path, such as `Exported 12 tracks to playlist(1).yaml.`
- A failed export prints one clear handled error instead of a success confirmation.
- Export rejects an empty TrackSequence with exit `2`; it never prints or saves an empty export.
- Redirected or piped stdout never prompts and never creates a file.
- `--links` output may only be saved as plain text.

An enriched title-and-artist `report` action is a future idea and remains separate from pure TrackSequence export.

## Search

```text
perfect-playlist search QUERY
perfect-playlist search QUERY --limit 8
perfect-playlist search QUERY --json
```

- Search discovers Spotify track candidates from human-readable query text and never writes or chooses automatically.
- The default candidate limit is `4`.
- `--limit` accepts `1` through `10`; invalid values exit `2`.
- Search has no `--market` option. Spotify uses the authenticated account's country.
- Search always searches tracks; item type is implicit.
- Human-readable candidate output is the default.
- `--json` returns structured command-response data for agents; it is not a Source or portable playlist type.
- Candidate output includes title, artists, explicit status, duration, URI, and Spotify link.
- An empty query exits `2` with a clear handled error.

## Inspect

```text
perfect-playlist inspect TRACK_REFERENCE
perfect-playlist inspect TRACK_REFERENCE --json
```

- Inspect confirms the exact Spotify metadata for one track URI or link.
- Human-readable output is the default.
- `--json` returns structured command-response data for agents; it is not a Source or portable playlist type.
- Output includes title, artists, explicit status, duration, URI, and Spotify link.
- An empty reference exits `2` with a clear handled error.

## Authentication

- A valid cached token is used silently.
- An expired token with a valid refresh path is refreshed silently.
- An interactive command that requires authorization prompts `Spotify authorization required. Log in now? [Y/n]`.
- After successful interactive browser authorization, resume the original command.
- A non-interactive command never opens a browser. It exits `2` with `Spotify authorization required. Run perfect-playlist auth login, then retry.`

## Exit Codes

- `0`: successful command.
- `1`: reserved exclusively for two valid Sources whose TrackSequences differ under Verify.
- `2`: every handled input, filesystem, authentication, Spotify, safety, or partial-write failure.

### Canonical YAML and JSON shape

YAML and JSON exports are self-describing objects containing only the TrackSequence:

```yaml
tracks:
  - spotify:track:354WZaV3u6cuzTG2PmpYwm
  - spotify:track:78APbsosmvDYIwZHjzC5ZE
```

```json
{
  "tracks": [
    "spotify:track:354WZaV3u6cuzTG2PmpYwm",
    "spotify:track:78APbsosmvDYIwZHjzC5ZE"
  ]
}
```

The schema contains everything required today while allowing compatible top-level fields later. Export does not add title, artist, album, or other descriptive metadata.

## Design Completion

No material product-language or CLI-behavior questions remain. Normal implementation details such as helper names, module boundaries, pagination mechanics, retry internals, and test fixture structure do not require another product decision as long as they preserve this contract.

Already settled and not open for reconsideration during implementation:

- Actions are top-level; `playlist` is not a command namespace.
- `build` is first-class; `add` is secondary and append-only.
- `repair` is removed.
- `resolve` is removed; AI agents use Search and Inspect to choose exact references before writing a TrackSequence.
- Build Target is owned and empty; public or private is accepted.
- Add accepts owned or collaborative, public or private writable playlists and never changes visibility.
- Verify compares two Sources as exact TrackSequences with count-first, first-position-only diagnostics.
- TrackSequence is canonical URI-only data; Links is a text export view.
- Export is non-destructive and has no force or overwrite option.
