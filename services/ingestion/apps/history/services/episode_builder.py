"""Deterministic, review-gated lifecycle episode skeletons."""
from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable
from apps.history.models import ReviewState

@dataclass(frozen=True)
class EpisodeSkeleton:
    subject_id: str
    scope: str
    phase: str
    date_min: object
    date_max: object
    claim_ids: tuple[str, ...]
    situation_claim_ids: tuple[str, ...]
    action_claim_ids: tuple[str, ...]
    result_claim_ids: tuple[str, ...]
    gap_claim_ids: tuple[str, ...]

def build_episode_skeletons(claims: Iterable[Any]) -> list[EpisodeSkeleton]:
    """Group reviewed claims without deriving chronology from uncertain intervals."""
    groups = defaultdict(list)
    for claim in claims:
        if claim.review_state != ReviewState.REVIEWED: continue
        phase = str((claim.value or {}).get("phase") or "UNSPECIFIED")
        scope = str((claim.value or {}).get("scope") or "company")
        groups[(str(claim.subject_id), scope, phase)].append(claim)
    skeletons=[]
    for (subject_id, scope, phase), rows in groups.items():
        ordered=sorted(rows, key=lambda c: (c.date_min is None, c.date_min or c.recorded_at.date(), str(c.id)))
        classified={"situation":[], "action":[], "result":[], "gap":[]}
        for claim in ordered:
            bucket = "action" if claim.claim_type == "documented_action" else "result" if claim.claim_type == "source_reported_outcome" else "situation" if claim.claim_type in {"measurement", "source_attributed_claim"} else "gap"
            classified[bucket].append(str(claim.id))
        mins=[c.date_min for c in rows if c.date_min]; maxs=[c.date_max for c in rows if c.date_max]
        skeletons.append(EpisodeSkeleton(subject_id, scope, phase, min(mins) if mins else None, max(maxs) if maxs else None, tuple(str(c.id) for c in ordered), tuple(classified["situation"]), tuple(classified["action"]), tuple(classified["result"]), tuple(classified["gap"])))
    return skeletons
