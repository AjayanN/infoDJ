"""Single review-gated projection owner for legacy domain readers."""
from __future__ import annotations
from typing import Any, Iterable
from apps.history.models import ReviewState

def projection_rows(claims: Iterable[Any]) -> list[dict[str, Any]]:
    rows=[]
    for claim in claims:
        if claim.review_state != ReviewState.REVIEWED: continue
        value=claim.value or {}
        if claim.track == "pricing" and value.get("kind") == "money":
            rows.append({"projection":"price", "claim_id":str(claim.id), "amount":value.get("amount"), "currency":value.get("currency"), "unit":value.get("unit"), "geography":value.get("geography"), "terms":value.get("terms"), "date_min":claim.date_min, "date_max":claim.date_max})
        elif claim.track in {"product", "legal_regulatory", "team"}:
            rows.append({"projection":claim.track, "claim_id":str(claim.id), "statement":claim.statement, "date_min":claim.date_min, "date_max":claim.date_max})
    return rows

def projection_fingerprint(row: dict[str, Any]) -> str:
    return f"history-claim:{row['claim_id']}:{row['projection']}"
