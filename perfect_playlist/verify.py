from __future__ import annotations

from .models import SourceVerificationResult, TrackSequence


def compare_track_sequences(
    left: TrackSequence,
    right: TrackSequence,
) -> SourceVerificationResult:
    """Compare two TrackSequences by count, then their first differing position."""
    if len(left) != len(right):
        return SourceVerificationResult(
            matches=False,
            left_count=len(left),
            right_count=len(right),
        )

    for index, (left_uri, right_uri) in enumerate(
        zip(left.uris, right.uris, strict=True), start=1
    ):
        if left_uri != right_uri:
            return SourceVerificationResult(
                matches=False,
                left_count=len(left),
                right_count=len(right),
                first_difference_position=index,
                left_uri=left_uri,
                right_uri=right_uri,
            )

    return SourceVerificationResult(
        matches=True,
        left_count=len(left),
        right_count=len(right),
    )
