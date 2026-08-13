from __future__ import annotations

from collections import Counter

from apps.accounts.founder_playbooks import playbook_for


DIRECTION_SPECS = (
    ("fastest_learning", "Fastest learning", "Run the smallest test that answers the stage question.", "questions"),
    ("lowest_risk", "Lowest risk", "Reduce the most material uncertainty before committing more resources.", "risks"),
    ("highest_upside", "Highest upside", "Test the path with the strongest potential to compound an advantage.", "metrics"),
)


def build_founder_decision(context: dict, companies: list[dict], dashboard: dict) -> dict:
    playbook = playbook_for(context.get("sector", ""), context.get("stage", ""))
    sector = context.get("sector", "")
    company_sectors = {str(row.get("slug") or ""): str(row.get("sector") or "") for row in companies}
    comparable_events = [
        event
        for event in dashboard.get("latest_events", [])
        if company_sectors.get(str(event.get("company_slug") or "")) == sector
        and event.get("source")
        and event.get("quality", {}).get("eligible")
    ]
    risk_events = [
        event
        for event in dashboard.get("risk_signals", [])
        if company_sectors.get(str(event.get("company_slug") or "")) == sector
        and event.get("source")
        and event.get("quality", {}).get("eligible")
    ]
    comparable_events = comparable_events[:12]
    risk_events = risk_events[:12]
    status = "available" if comparable_events else "insufficient_evidence"

    directions = []
    for index, (key, title, default_action, playbook_key) in enumerate(DIRECTION_SPECS):
        evidence = comparable_events[index::len(DIRECTION_SPECS)][:3]
        directions.append(
            {
                "key": key,
                "title": title,
                "claim_type": "founder_hypothesis",
                "next_action": (
                    playbook[playbook_key][0]
                    if playbook.get(playbook_key)
                    else default_action
                ),
                "why_now": playbook["stage_question"],
                "evidence": [serialize_event(event) for event in evidence],
                "evidence_status": "observed_pattern" if evidence else "unavailable",
            }
        )

    risk_counts = Counter(str(event.get("event_type") or "OTHER") for event in risk_events)
    return {
        "status": status,
        "context": context,
        "playbook": playbook,
        "directions": directions,
        "journey": [serialize_event(event) for event in sorted(comparable_events, key=lambda row: str(row.get("event_date") or ""))],
        "risk_radar": [
            {
                "label": label.replace("_", " ").title(),
                "count": count,
                "claim_type": "reported_fact",
            }
            for label, count in risk_counts.most_common(5)
        ],
        "coverage": {
            "comparable_event_count": len(comparable_events),
            "risk_event_count": len(risk_events),
            "sector_company_count": sum(1 for row in companies if row.get("sector") == sector),
            "evidence_policy": "Only dated eligible events with a linked source are used as comparable evidence.",
        },
        "source_gaps": (
            []
            if comparable_events
            else [
                {
                    "key": "founder_decision_evidence",
                    "reason": f"No eligible, source-linked comparable events are available for {sector or 'the selected sector'}.",
                    "next_action": "Run sector ingestion and review eligible events before relying on a decision path.",
                }
            ]
        ),
    }


def serialize_event(event: dict) -> dict:
    source = event.get("source") or {}
    return {
        "id": event.get("id"),
        "company": event.get("company"),
        "company_slug": event.get("company_slug"),
        "event_date": event.get("event_date"),
        "event_type": event.get("event_type"),
        "actual_change": event.get("actual_change"),
        "confidence_score": event.get("confidence_score"),
        "source": {
            "title": source.get("title"),
            "url": source.get("url"),
            "published_date": source.get("published_date"),
        },
        "claim_type": "reported_fact",
    }
