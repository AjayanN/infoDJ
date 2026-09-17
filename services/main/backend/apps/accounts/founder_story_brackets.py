"""Source-linked historical case brackets for founder onboarding.

A bracket is deliberately not a recommendation or a claim of comparability.  It
places a reviewed company action beside the next question a founder must answer.
"""
from __future__ import annotations


def build_story_brackets(companies: list[dict], dashboard: dict, sector: str, *, limit: int = 50) -> dict:
    sectors = {str(row.get("slug") or ""): str(row.get("sector") or "") for row in companies}
    events = [*dashboard.get("historical_events", []), *dashboard.get("latest_events", [])]
    seen, selected = set(), []
    for event in events:
        identity = event.get("id")
        if identity in seen:
            continue
        seen.add(identity)
        if sectors.get(str(event.get("company_slug") or "")) != sector:
            continue
        if not event.get("source") or not event.get("quality", {}).get("eligible"):
            continue
        timing = event.get("lifecycle_timing") or {}
        if not timing.get("eligible") or timing.get("action_date_precision") != "DAY":
            continue
        if not str(event.get("actual_change") or "").strip():
            continue
        selected.append(event)
    selected.sort(key=lambda row: (str((row.get("lifecycle_timing") or {}).get("action_date") or row.get("event_date") or ""), str(row.get("company") or "")))
    brackets = [serialize_bracket(event) for event in selected[:limit]]
    return {
        "status": "available" if brackets else "insufficient_evidence",
        "sector": sector,
        "brackets": brackets,
        "source_gaps": [] if brackets else [{
            "key": "founder_story_brackets",
            "reason": f"No reviewed, source-linked historical case bracket is available for {sector or 'the selected field'} yet.",
            "next_action": "Ask the founder directly, then review an authoritative dated source before adding a company case.",
        }],
    }


def serialize_bracket(event: dict) -> dict:
    source = event.get("source") or {}
    timing = event.get("lifecycle_timing") or {}
    action = str(event.get("actual_change") or "").strip()
    problem = str(event.get("trigger") or "").strip()
    before = str(event.get("before_state") or "").strip()
    outcome = str(event.get("outcome") or "").strip()
    return {
        "company": event.get("company"),
        "company_slug": event.get("company_slug"),
        "event_date": timing.get("action_date") or event.get("event_date"),
        "event_type": event.get("event_type"),
        "documented_action": action,
        "situation": before,
        "documented_problem": problem,
        "documented_outcome": outcome,
        "question": question_for(event, problem),
        "claim_type": "reported_fact",
        "source": {"title": source.get("title"), "url": source.get("url")},
        "evidence_note": "This is one source-linked case, not proof that the same action will work for your company.",
    }


def question_for(event: dict, problem: str) -> str:
    theme = str(event.get("decision_theme") or "").replace("_", " ").lower()
    if problem:
        return f"What customer problem are you testing, and what is the smallest action that can test it? ({theme or 'documented company action'} is context only.)"
    return "What customer problem, product decision, and evidence would make this case relevant—or clearly different—for you?"
