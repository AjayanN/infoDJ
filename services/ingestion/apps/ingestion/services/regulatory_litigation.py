from __future__ import annotations

import re
from datetime import date

from apps.companies.models import (
    Company,
    CompanyProfileStatus,
    RegulatoryLitigationMatter,
    RegulatoryLitigationSnapshot,
    RegulatoryMateriality,
    RegulatoryMatterStage,
    RegulatoryMatterStatus,
    RegulatoryMatterType,
)
from apps.curation.models import BusinessEvent
from apps.ingestion.models import SourceDocument


LEGAL_GUARDRAIL = (
    "This calendar records disclosed matters and procedural context only. It does not make legal conclusions, "
    "predict outcomes, or estimate exposure unless a reviewed source states it."
)


def build_regulatory_litigation_calendar(company: Company) -> dict[str, int]:
    events = list(
        BusinessEvent.objects.filter(company=company, event_type="REGULATORY_RESPONSE", review_status__in=["NEEDS_REVIEW", "APPROVED"])
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:30]
    )
    effective_date = next((event.event_date for event in events if event.event_date), None) or date.today()
    source = latest_source(company)
    snapshot, created = RegulatoryLitigationSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        defaults={
            "source_document": source,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": summary_for(company, events),
            "methodology": (
                "Built from reviewed regulatory-response business events and linked source documents. "
                "Open matters, authorities, deadlines, and exposure are shown only where the reviewed source text supports them."
            ),
            "legal_guardrail": LEGAL_GUARDRAIL,
            "confidence_score": "0.780" if events else "0.600",
        },
    )
    created_count = updated_count = 0
    keep_ids: set[int] = set()
    for event in events:
        matter, was_created = RegulatoryLitigationMatter.objects.update_or_create(
            snapshot=snapshot,
            title=matter_title(event),
            matter_type=matter_type(event),
            opened_date=event.event_date,
            defaults={
                "linked_event": event,
                "jurisdiction": infer_jurisdiction(event),
                "authority": infer_authority(event),
                "business_area": infer_business_area(event),
                "stage": infer_stage(event),
                "matter_status": infer_status(event),
                "materiality": infer_materiality(event),
                "next_date": None,
                "next_date_type": "",
                "allegation_or_issue": clean(event.source_claim or event.trigger or event.before_state),
                "company_response": clean(event.actual_change or event.decision or event.after_state),
                "interim_decision": interim_decision(event),
                "final_outcome": final_outcome(event),
                "exposure_context": exposure_context(event),
                "evidence_text": clean(event.evidence_text or event.source_claim or event.actual_change),
                "source_document": event.source_document,
                "confidence_score": event.confidence_score,
                "review_status": "REVIEWED",
            },
        )
        keep_ids.add(matter.id)
        created_count += 1 if was_created else 0
        updated_count += 0 if was_created else 1
    snapshot.matters.exclude(id__in=keep_ids).delete()
    return {
        "snapshots_created": 1 if created else 0,
        "snapshots_updated": 0 if created else 1,
        "matters_created": created_count,
        "matters_updated": updated_count,
    }


def regulatory_litigation_quality_issues(company: Company) -> list[str]:
    snapshot = (
        RegulatoryLitigationSnapshot.objects.filter(company=company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .prefetch_related("matters")
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if snapshot is None:
        return ["no reviewed regulatory and litigation snapshot"]
    issues: list[str] = []
    if not snapshot.legal_guardrail:
        issues.append("legal guardrail unavailable")
    if not snapshot.matters.exists():
        issues.append("no reviewed regulatory or litigation matters")
    if not snapshot.matters.exclude(next_date__isnull=True).exists():
        issues.append("no sourced future deadlines")
    return issues


def latest_source(company: Company) -> SourceDocument | None:
    return SourceDocument.objects.filter(company=company).order_by("-published_date", "-updated_at").first()


def summary_for(company: Company, events: list[BusinessEvent]) -> str:
    if not events:
        return f"No reviewed regulatory or litigation matters are available for {company.name}."
    return f"{company.name} has {len(events)} reviewed regulatory-response event(s) available for procedural tracking."


def matter_title(event: BusinessEvent) -> str:
    text = clean(event.decision or event.actual_change or event.source_claim or event.trigger)
    if not text:
        return "Regulatory or litigation matter"
    return text[:180].rstrip(".")


def matter_type(event: BusinessEvent) -> str:
    text = event_text(event)
    if has_any(text, "settlement", "settled", "consent decree"):
        return RegulatoryMatterType.SETTLEMENT
    if has_any(text, "lawsuit", "litigation", "court", "complaint", "class action", "appeal"):
        return RegulatoryMatterType.LITIGATION
    if has_any(text, "investigation", "subpoena", "probe", "inquiry"):
        return RegulatoryMatterType.INVESTIGATION
    if has_any(text, "approval", "approved", "clearance", "authorized", "license"):
        return RegulatoryMatterType.APPROVAL
    if has_any(text, "compliance", "obligation", "deadline", "remediation"):
        return RegulatoryMatterType.COMPLIANCE_OBLIGATION
    if has_any(text, "regulator", "regulatory", "agency", "commission"):
        return RegulatoryMatterType.REGULATORY_REVIEW
    return RegulatoryMatterType.OTHER


def infer_stage(event: BusinessEvent) -> str:
    text = event_text(event)
    if has_term(text, "closed", "resolved", "completed", "final"):
        return RegulatoryMatterStage.CLOSED
    if has_any(text, "appeal", "appealed"):
        return RegulatoryMatterStage.APPEAL
    if has_any(text, "hearing", "trial"):
        return RegulatoryMatterStage.HEARING
    if has_any(text, "decision pending", "awaiting decision", "pending approval"):
        return RegulatoryMatterStage.DECISION_PENDING
    if has_any(text, "investigation", "probe", "inquiry", "subpoena"):
        return RegulatoryMatterStage.INVESTIGATION
    if has_any(text, "filed", "complaint"):
        return RegulatoryMatterStage.FILED
    if has_any(text, "compliance", "remediation"):
        return RegulatoryMatterStage.COMPLIANCE
    if has_any(text, "review", "approval", "clearance"):
        return RegulatoryMatterStage.REVIEW
    return RegulatoryMatterStage.IDENTIFIED if event.event_date else RegulatoryMatterStage.UNKNOWN


def infer_status(event: BusinessEvent) -> str:
    text = event_text(event)
    if has_any(text, "settled", "settlement"):
        return RegulatoryMatterStatus.SETTLED
    if has_term(text, "dismissed"):
        return RegulatoryMatterStatus.DISMISSED
    if has_term(text, "approved", "clearance", "authorized"):
        return RegulatoryMatterStatus.APPROVED
    if has_term(text, "closed", "resolved", "completed"):
        return RegulatoryMatterStatus.CLOSED
    if has_any(text, "pending", "awaiting", "ongoing", "investigation"):
        return RegulatoryMatterStatus.PENDING
    return RegulatoryMatterStatus.OPEN


def infer_materiality(event: BusinessEvent) -> str:
    text = event_text(event)
    if has_any(text, "material", "significant", "billion", "million", "fine", "penalty", "consent decree"):
        return RegulatoryMateriality.MATERIAL
    if has_any(text, "risk", "could", "may", "investigation", "lawsuit", "litigation"):
        return RegulatoryMateriality.WATCH
    return RegulatoryMateriality.DISCLOSED


def infer_jurisdiction(event: BusinessEvent) -> str:
    text = event_text(event)
    if has_any(text, "european", "eu ", "e.u.", "europe"):
        return "European Union"
    if has_any(text, "united states", "u.s.", "us ", "sec ", "ftc ", "doj "):
        return "United States"
    if has_any(text, "china", "chinese"):
        return "China"
    if has_any(text, "india"):
        return "India"
    if has_any(text, "uk ", "united kingdom", "britain"):
        return "United Kingdom"
    return ""


def infer_authority(event: BusinessEvent) -> str:
    text = event_text(event)
    authorities = [
        ("SEC", ("sec ", "securities and exchange commission")),
        ("FTC", ("ftc ", "federal trade commission")),
        ("DOJ", ("doj ", "department of justice")),
        ("European Commission", ("european commission",)),
        ("EPA", ("epa ", "environmental protection agency")),
        ("FDA", ("fda ", "food and drug administration")),
        ("NHTSA", ("nhtsa",)),
    ]
    for label, needles in authorities:
        if has_any(text, *needles):
            return label
    return ""


def infer_business_area(event: BusinessEvent) -> str:
    text = event_text(event)
    areas = [
        ("Data/privacy", ("privacy", "data protection", "data security")),
        ("Competition/antitrust", ("antitrust", "competition", "monopoly")),
        ("Consumer protection", ("consumer", "advertising", "marketing claim")),
        ("Labor/employment", ("labor", "employment", "worker", "union")),
        ("Environmental/safety", ("environment", "emission", "safety", "recall")),
        ("Financial reporting", ("accounting", "financial reporting", "securities")),
        ("M&A approval", ("merger", "acquisition", "approval", "clearance")),
    ]
    for label, needles in areas:
        if has_any(text, *needles):
            return label
    return ""


def interim_decision(event: BusinessEvent) -> str:
    text = clean(event.outcome)
    return text if text and not has_any(text.lower(), "final", "settled", "dismissed", "closed") else ""


def final_outcome(event: BusinessEvent) -> str:
    text = clean(event.outcome)
    return text if has_any(text.lower(), "final", "settled", "dismissed", "closed", "approved") else ""


def exposure_context(event: BusinessEvent) -> str:
    text = clean(" ".join([event.source_claim or "", event.actual_change or "", event.outcome or "", event.evidence_text or ""]))
    if re.search(r"\$[\d,.]+\s*(million|billion|m|bn)?|penalt(?:y|ies)|fine|remediation cost|liability", text, re.IGNORECASE):
        return text[:500]
    return ""


def event_text(event: BusinessEvent) -> str:
    return " ".join(
        clean(part).lower()
        for part in [event.source_claim, event.actual_change, event.evidence_text, event.outcome, event.trigger, event.decision]
        if part
    )


def clean(value: str | None) -> str:
    return " ".join((value or "").split())


def has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def has_term(text: str, *needles: str) -> bool:
    return any(re.search(rf"\b{re.escape(needle)}\b", text) for needle in needles)
