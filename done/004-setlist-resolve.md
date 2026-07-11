# Task 004: Setlist Resolve Workflow

Status: done

Implemented a search-only resolver for human-readable YAML setlists. Unique
exact title/artist matches receive an exact Spotify URI. Ambiguous or unmatched
entries are marked `needs_review: true` and include candidate URIs for manual
approval. The resolver never creates or modifies playlists.

CLI:

```powershell
perfect-playlist resolve setlist setlist.yaml --out resolved.yaml
```

Verification:

- Unique exact matches are selected.
- Ambiguous matches remain reviewable and are excluded from `manifest.uris`.
- Search queries are sent in input order.
- Existing full-suite tests remain green.
