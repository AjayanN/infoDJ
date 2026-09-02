from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from apps.accounts.founder_playbooks import playbook_for


DIRECTION_SPECS = (
    ("fastest_learning", "Fastest learning", "Run the smallest test that answers the stage question.", "questions"),
    ("lowest_risk", "Lowest risk", "Reduce the most material uncertainty before committing more resources.", "risks"),
    ("highest_upside", "Highest upside", "Test the path with the strongest potential to compound an advantage.", "metrics"),
)

FRESH_EVIDENCE_WINDOW = timedelta(days=365)
# A founder stage is a company-lifecycle claim, not a topic label.
# The bands are deliberately conservative: abstain when the corpus cannot establish
# a same-stage comparison instead of borrowing a mature-company move.
FOUNDER_STAGE_COMPARISON_RULES = {
    "validate": ({"IDEA", "LAUNCH"}, 0, 730),
    "build": ({"IDEA", "LAUNCH"}, 0, 1095),
    "launch": ({"LAUNCH", "EARLY_GROWTH"}, 90, 1460),
    "grow": ({"EARLY_GROWTH", "SCALE"}, 180, 2920),
    "scale": ({"SCALE"}, 730, None),
}


def is_stage_comparable(event: dict, founder_stage: str) -> bool:
    allowed_stages, min_age_days, max_age_days = FOUNDER_STAGE_COMPARISON_RULES.get(founder_stage, (set(), 0, -1))
    timing = event.get("lifecycle_timing") or {}
    lifecycle_stage = str(timing.get("company_lifecycle_stage") or "")
    if lifecycle_stage not in allowed_stages:
        return False
    company_age_days = timing.get("company_age_days")
    if isinstance(company_age_days, int):
        return company_age_days >= min_age_days and (max_age_days is None or company_age_days <= max_age_days)

    age_range = timing.get("company_age_days_range") or {}
    minimum = age_range.get("minimum")
    maximum = age_range.get("maximum")
    if not isinstance(minimum, int) or not isinstance(maximum, int):
        return False
    return minimum >= min_age_days and (max_age_days is None or maximum <= max_age_days)



def build_founder_decision(context: dict, companies: list[dict], dashboard: dict) -> dict:
    playbook = playbook_for(context.get("sector", ""), context.get("stage", ""))
    sector = context.get("sector", "")
    company_sectors = {str(row.get("slug") or ""): str(row.get("sector") or "") for row in companies}
    candidate_events = [
        *dashboard.get("historical_events", []),
        *dashboard.get("latest_events", []),
    ]
    seen_event_ids = set()
    comparable_events = []
    for event in candidate_events:
        event_id = event.get("id")
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)
        if (
            company_sectors.get(str(event.get("company_slug") or "")) == sector
            and event.get("source")
            and is_stage_comparable(event, str(context.get("stage") or ""))
            and event.get("quality", {}).get("eligible")
            and event.get("lifecycle_timing", {}).get("eligible")
        ):
            comparable_events.append(event)
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
                "reasoning": direction_reasoning(
                    stage_question=playbook["stage_question"],
                    action=(playbook[playbook_key][0] if playbook.get(playbook_key) else default_action),
                    evidence=evidence,
                ),
                "evidence": [serialize_event(event) for event in evidence],
                "company_names": sorted({str(event.get("company") or "") for event in evidence if event.get("company")}),
                "evidence_status": "observed_pattern" if evidence else "unavailable",
            }
        )

    risk_counts = Counter(str(event.get("event_type") or "OTHER") for event in risk_events)
    coverage_passport = build_coverage_passport(comparable_events, risk_events, companies, sector)
    return {
        "status": status,
        "context": context,
        "playbook": playbook,
        "directions": directions,
        "journey": [serialize_event(event) for event in sorted(comparable_events, key=lambda row: str((row.get("lifecycle_timing") or {}).get("action_date") or row.get("event_date") or ""))],
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
            "evidence_policy": "Founder comparisons require a source-linked exact action date, verified founding anchor, source-backed lifecycle stage, and an exact age or bounded age range wholly inside the selected stage band.",
        },
        "coverage_passport": coverage_passport,
        "source_gaps": (
            []
            if comparable_events
            else [
                {
                    "key": "founder_decision_evidence",
                    "reason": f"No stage-matched, source-linked comparable moves are available for {sector or 'the selected sector'} at the selected lifecycle stage.",
                    "next_action": "Backfill historical primary sources with company age and source-backed stage-at-action evidence before relying on a decision path.",
                }
            ]
        ),
    }


def build_coverage_passport(comparable_events: list[dict], risk_events: list[dict], companies: list[dict], sector: str) -> list[dict]:
    sector_companies = [row for row in companies if row.get("sector") == sector]
    dates = [parse_event_date(event.get("event_date")) for event in comparable_events]
    latest_date = max((value for value in dates if value), default=None)
    source_urls = {
        str((event.get("source") or {}).get("url") or "")
        for event in [*comparable_events, *risk_events]
        if (event.get("source") or {}).get("url")
    }
    is_stale = bool(latest_date and latest_date < date.today() - FRESH_EVIDENCE_WINDOW)
    comparable_status = "missing" if not comparable_events else "stale" if is_stale else "available"
    return [
        passport_item("Comparable moves", comparable_status, len(comparable_events), latest_date.isoformat() if latest_date else None, "Dated, source-linked strategic moves from companies in your selected field.", "Run sector ingestion and review comparable company events."),
        passport_item("Risk signals", "available" if risk_events else "missing", len(risk_events), latest_date.isoformat() if latest_date else None, "Source-linked risks that may affect a founder's next decision.", "Collect and review sector risk disclosures before treating risks as comparable evidence."),
        passport_item("Peer landscape", "available" if len(sector_companies) >= 2 else "missing", len(sector_companies), None, "Configured companies available for same-sector comparison.", "Add or classify more companies in this field before drawing peer conclusions."),
        passport_item("Source diversity", "available" if len(source_urls) >= 2 else "missing", len(source_urls), latest_date.isoformat() if latest_date else None, "Distinct direct sources behind the founder cockpit evidence.", "Collect at least two direct sources before relying on a pattern."),
    ]


def passport_item(label: str, status: str, count: int, last_observed_on: str | None, description: str, next_action: str) -> dict:
    strength = "strong" if count >= 6 else "moderate" if count >= 3 else "weak" if count else "missing"
    return {"label": label, "status": status, "evidence_strength": strength, "count": count, "last_observed_on": last_observed_on, "claim_type": "reported_fact", "description": description, "next_action": next_action}


def direction_reasoning(*, stage_question: str, action: str, evidence: list[dict]) -> str:
    """Explain the recommendation without presenting the hypothesis as a reported fact."""

    if not evidence:
        return f"This is a focused starting hypothesis for the question: {stage_question}"
    companies = sorted({str(event.get("company") or "") for event in evidence if event.get("company")})
    company_text = ", ".join(companies[:3])
    return (
        f"At this stage, the decision to make is: {stage_question} "
        f"The suggested next action is {action.lower()} "
        f"because InfoDJ has dated, source-linked moves from {company_text} that you can inspect before deciding."
    )


def parse_event_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


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
        "lifecycle_timing": event.get("lifecycle_timing") or {},
        "source": {
            "title": source.get("title"),
            "url": source.get("url"),
            "published_date": source.get("published_date"),
        },
        "claim_type": "reported_fact",
    }
