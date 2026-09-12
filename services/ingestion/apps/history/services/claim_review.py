"""Append-only review and explicit claim supersession services."""
from __future__ import annotations

from django.db import transaction

from apps.history.models import ClaimReview, HistoricalClaim, ReviewState


@transaction.atomic
def record_review(*, claim: HistoricalClaim, decision: str, reviewer: str, rationale: str, reviewer_type: str = "staff", conflict_group: str = "", resolution_options: list[str] | None = None) -> ClaimReview:
    if decision not in {ReviewState.REVIEWED, ReviewState.REJECTED, ReviewState.CONFLICTED, ReviewState.PENDING, ReviewState.SUPERSEDED}:
        raise ValueError("Review decision is not valid.")
    if not reviewer or not rationale:
        raise ValueError("Reviewer and rationale are required.")
    review = ClaimReview.objects.create(claim=claim, decision=decision, reviewer=reviewer, reviewer_type=reviewer_type, rationale=rationale, conflict_group=conflict_group, resolution_options=resolution_options or [])
    HistoricalClaim.objects.filter(pk=claim.pk).update(review_state=decision)
    return review


@transaction.atomic
def supersede_claim(*, prior: HistoricalClaim, replacement: HistoricalClaim, reviewer: str, rationale: str) -> ClaimReview:
    if replacement.supersedes_id:
        raise ValueError("Replacement claim already supersedes another claim.")
    HistoricalClaim.objects.filter(pk=replacement.pk).update(supersedes=prior)
    return record_review(claim=prior, decision=ReviewState.SUPERSEDED, reviewer=reviewer, rationale=rationale)
