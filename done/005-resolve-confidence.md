# Task 005: Resolve Confidence Metadata

Status: done

Added explicit confidence metadata to resolved setlist entries. Scores are
based on exact title and artist agreement: each contributes `0.5`, for a
maximum confidence of `1.0`. A unique `1.0` candidate can be suggested, but
duplicate high-confidence candidates still require review.

Verification:

- Unique exact matches receive confidence `1.0` and a URI.
- Ambiguous high-confidence matches receive confidence `1.0` but remain marked
  `needs_review: true`.
- The resolver remains search-only and never writes to Spotify.
