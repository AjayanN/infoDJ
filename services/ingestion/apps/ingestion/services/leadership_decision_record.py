from __future__ import annotations

from datetime import date
import re

from apps.companies.models import (
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    LeadershipDecisionRecord,
    LeadershipDecisionSnapshot,
    LeadershipDecisionType,
    LeadershipRoleRecord,
    LeadershipRoleType,
    LeadershipTransitionType,
)
from apps.curation.models import BusinessEvent, StrategicTurn
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


def build_leadership_decision_record(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    source = profile.source_document if profile else latest_source(company)
    effective_date = profile.effective_date if profile else date.today()
    roles = role_specs(company, profile, source)
    decisions = decision_specs(company, profile, source)
    snapshot, created = LeadershipDecisionSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": leadership_summary(company, roles, decisions),
            "methodology": (
                "Baseline generated from reviewed Company 360 leadership, reviewed leadership-change events, "
                "strategic priorities, and reviewed strategic turns. Departure reasons, personal allegations, "
                "compensation goals, and performance attribution are not inferred."
            ),
            "non_causation_note": (
                "Performance during a leader's tenure is contextual. This record does not claim that a leader caused "
                "stock, financial, or operational outcomes unless a reviewed source explicitly supports that claim."
            ),
            "confidence_score": "0.800" if roles or decisions else "0.600",
        },
    )
    counters = {"snapshots_created": 1 if created else 0, "snapshots_updated": 0 if created else 1, "roles_created": 0, "roles_updated": 0, "decisions_created": 0, "decisions_updated": 0}
    keep_role_ids = set()
    for spec in roles:
        role, was_created = LeadershipRoleRecord.objects.update_or_create(
            snapshot=snapshot,
            leader_name=spec["leader_name"],
            role_title=spec["role_title"],
            transition_type=spec["transition_type"],
            defaults={
                "role_type": spec["role_type"],
                "start_date": spec["start_date"],
                "end_date": spec["end_date"],
                "interim_status": spec["interim_status"],
                "co_leadership": spec["co_leadership"],
                "stated_priorities": spec["stated_priorities"],
                "evidence_text": spec["evidence_text"],
                "source_document": spec["source_document"],
                "linked_event": spec["linked_event"],
                "confidence_score": spec["confidence_score"],
                "review_status": "REVIEWED",
            },
        )
        keep_role_ids.add(role.id)
        counters["roles_created" if was_created else "roles_updated"] += 1
    keep_decision_ids = set()
    for spec in decisions:
        decision, was_created = LeadershipDecisionRecord.objects.update_or_create(
            snapshot=snapshot,
            title=spec["title"],
            decision_type=spec["decision_type"],
            decision_date=spec["decision_date"],
            defaults={
                "leader_name": spec["leader_name"],
                "summary": spec["summary"],
                "evidence_text": spec["evidence_text"],
                "source_document": spec["source_document"],
                "linked_event": spec["linked_event"],
                "linked_strategic_turn": spec["linked_strategic_turn"],
                "confidence_score": spec["confidence_score"],
                "review_status": "REVIEWED",
            },
        )
        keep_decision_ids.add(decision.id)
        counters["decisions_created" if was_created else "decisions_updated"] += 1
    if keep_role_ids:
        snapshot.roles.exclude(id__in=keep_role_ids).delete()
    if keep_decision_ids:
        snapshot.decisions.exclude(id__in=keep_decision_ids).delete()
    return counters


def leadership_decision_quality_issues(company: Company) -> list[str]:
    snapshot = (
        LeadershipDecisionSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("roles", "decisions")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed leadership decision snapshot"]
    issues = []
    if not snapshot.roles.exists():
        issues.append("no reviewed leadership roles")
    if not snapshot.roles.exclude(start_date__isnull=True).exists():
        issues.append("tenure start dates unavailable")
    if not snapshot.decisions.exists():
        issues.append("no reviewed leadership-linked decisions")
    return issues


def latest_profile(company: Company) -> CompanyProfileSnapshot | None:
    return (
        CompanyProfileSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .select_related("source_document")
        .order_by("-effective_date", "-updated_at")
        .first()
    )


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def role_specs(company: Company, profile: CompanyProfileSnapshot | None, source: SourceDocument | None) -> list[dict[str, object]]:
    rows = []
    leaders = profile.leadership if profile and isinstance(profile.leadership, list) else []
    if not leaders:
        leaders = PROFILE_FALLBACKS.get(company.slug, {}).get("leadership", [])
    priorities = profile.strategic_priorities if profile and isinstance(profile.strategic_priorities, list) else []
    for raw in leaders:
        name, title = parse_leader(raw)
        if not name:
            continue
        rows.append({
            "leader_name": name[:255],
            "role_title": title[:255],
            "role_type": role_type_for(title),
            "transition_type": LeadershipTransitionType.CURRENT_ROLE,
            "start_date": None,
            "end_date": None,
            "interim_status": "interim" in title.lower(),
            "co_leadership": "co-" in title.lower() or "co " in title.lower(),
            "stated_priorities": [clean_label(str(row)) for row in priorities[:5] if clean_label(str(row))],
            "evidence_text": f"Reviewed Company 360 leadership context for {name}" + (f" as {title}" if title else "") + ".",
            "source_document": source,
            "linked_event": None,
            "confidence_score": "0.800",
        })
    for event in leadership_events(company):
        name = event_leader_name(event)
        if not name:
            name = "Leadership change"
        rows.append({
            "leader_name": name[:255],
            "role_title": event.decision_theme.replace("_", " ").title() if event.decision_theme else "",
            "role_type": role_type_for(event.decision_theme or event.actual_change or ""),
            "transition_type": transition_type_for(event),
            "start_date": event.event_date,
            "end_date": None,
            "interim_status": "interim" in event_text(event).lower(),
            "co_leadership": "co-" in event_text(event).lower(),
            "stated_priorities": [],
            "evidence_text": event.evidence_text or event.actual_change or event.source_claim,
            "source_document": event.source_document or source,
            "linked_event": event,
            "confidence_score": "0.760",
        })
    return unique_roles(rows)


def decision_specs(company: Company, profile: CompanyProfileSnapshot | None, source: SourceDocument | None) -> list[dict[str, object]]:
    rows = []
    priorities = profile.strategic_priorities if profile and isinstance(profile.strategic_priorities, list) else []
    leader_name = first_leader_name(profile, company)
    for priority in priorities[:8]:
        label = clean_label(str(priority))
        if not label:
            continue
        rows.append(decision_spec(label, LeadershipDecisionType.STRATEGIC_PRIORITY, None, leader_name, label, f"Reviewed strategic priority: {label}.", source, None, None, "0.780"))
    for event in leadership_events(company):
        title = event.actual_change or event.source_claim or "Leadership change"
        rows.append(decision_spec(clean_label(title)[:255], LeadershipDecisionType.SUCCESSION, event.event_date, event_leader_name(event), title, event.evidence_text or title, event.source_document or source, event, None, "0.760"))
    for turn in StrategicTurn.objects.filter(company=company, is_published=True, review_status="REVIEWED").order_by("-start_date", "-created_at")[:8]:
        rows.append(decision_spec(turn.title, LeadershipDecisionType.MATERIAL_DECISION, turn.start_date, leader_name, turn.summary or turn.title, turn.evidence_text or turn.summary or turn.title, source, None, turn, "0.720"))
    return unique_decisions(rows)


def decision_spec(title, decision_type, decision_date, leader_name, summary, evidence_text, source, event, turn, confidence):
    return {
        "title": title[:255],
        "decision_type": decision_type,
        "decision_date": decision_date,
        "leader_name": (leader_name or "")[:255],
        "summary": summary,
        "evidence_text": evidence_text,
        "source_document": source,
        "linked_event": event,
        "linked_strategic_turn": turn,
        "confidence_score": confidence,
    }


def leadership_events(company: Company) -> list[BusinessEvent]:
    return list(
        BusinessEvent.objects.filter(company=company, event_type="LEADERSHIP_CHANGE")
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:12]
    )


def parse_leader(raw: object) -> tuple[str, str]:
    if isinstance(raw, dict):
        return clean_label(str(raw.get("name") or raw.get("person") or "")), clean_label(str(raw.get("role") or raw.get("title") or ""))
    value = clean_label(str(raw))
    if not value:
        return "", ""
    parts = re.split(r"\s+-\s+|\s+,\s+", value, maxsplit=1)
    return clean_label(parts[0]), clean_label(parts[1]) if len(parts) > 1 else ""


def first_leader_name(profile: CompanyProfileSnapshot | None, company: Company) -> str:
    leaders = profile.leadership if profile and isinstance(profile.leadership, list) else PROFILE_FALLBACKS.get(company.slug, {}).get("leadership", [])
    for row in leaders:
        name, _title = parse_leader(row)
        if name:
            return name
    return ""


def role_type_for(text: str) -> str:
    lowered = text.lower()
    if "chief executive" in lowered or "ceo" in lowered:
        return LeadershipRoleType.CEO
    if "chief financial" in lowered or "cfo" in lowered:
        return LeadershipRoleType.CFO
    if "chief operating" in lowered or "coo" in lowered:
        return LeadershipRoleType.COO
    if "chair" in lowered:
        return LeadershipRoleType.CHAIR
    if "director" in lowered:
        return LeadershipRoleType.DIRECTOR
    if "board" in lowered:
        return LeadershipRoleType.BOARD
    return LeadershipRoleType.EXECUTIVE if text else LeadershipRoleType.UNKNOWN


def transition_type_for(event: BusinessEvent) -> str:
    lowered = event_text(event).lower()
    if "depart" in lowered or "resign" in lowered or "retire" in lowered:
        return LeadershipTransitionType.DEPARTURE
    if "succession" in lowered or "succeed" in lowered:
        return LeadershipTransitionType.SUCCESSION_PLAN
    if "board" in lowered:
        return LeadershipTransitionType.BOARD_CHANGE
    if "appoint" in lowered or "named" in lowered or "become" in lowered:
        return LeadershipTransitionType.APPOINTMENT
    return LeadershipTransitionType.ROLE_CHANGE


def event_leader_name(event: BusinessEvent) -> str:
    text = event_text(event)
    match = re.search(r"\b([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})\b", text)
    return clean_label(match.group(1)) if match else ""


def event_text(event: BusinessEvent) -> str:
    return " ".join([event.actual_change or "", event.source_claim or "", event.evidence_text or "", event.decision_theme or ""])


def leadership_summary(company: Company, roles: list[dict[str, object]], decisions: list[dict[str, object]]) -> str:
    if not roles and not decisions:
        return f"No reviewed leadership decision record is available for {company.name}."
    return f"{company.name} has {len(roles)} reviewed leadership role rows and {len(decisions)} reviewed priority or decision rows."


def unique_roles(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    unique = []
    for row in rows:
        key = (str(row["leader_name"]).lower(), str(row["role_title"]).lower(), row["transition_type"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def unique_decisions(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    seen = set()
    unique = []
    for row in rows:
        key = (str(row["title"]).lower(), row["decision_type"], row["decision_date"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .;:-")
