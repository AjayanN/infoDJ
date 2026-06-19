from __future__ import annotations

import re
from datetime import date

from django.utils.text import slugify

from apps.companies.models import (
    AcquisitionLifecycleDeal,
    AcquisitionLifecycleEvent,
    AcquisitionOutcomeCategory,
    AcquisitionStage,
    AcquisitionTransactionType,
    Company,
    CompanyProfileSnapshot,
    CompanyProfileStatus,
    PromiseReviewStatus,
)
from apps.curation.models import BusinessEvent, StrategicTurn
from apps.ingestion.models import SourceDocument
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


ACQUISITION_TERMS = ("acquired", "acquisition", "merger", "combined", "business combination")
DIVESTITURE_TERMS = ("divested", "divestiture", "sold", "sale of")
IMPAIRMENT_TERMS = ("impairment", "write-down", "written down", "writedown")


def build_acquisition_lifecycle(company: Company) -> dict[str, int]:
    profile = latest_profile(company)
    source = profile.source_document if profile else latest_source(company)
    effective_date = profile.effective_date if profile else date.today()
    counters = {"deals_created": 0, "deals_updated": 0, "events_created": 0, "events_updated": 0}
    purge_generic_event_deals(company)
    fallback_targets = profile_targets(company, profile)
    purge_profile_deals_not_in_targets(company, fallback_targets)

    for event in acquisition_events(company):
        target_name = target_from_event(event)
        if not target_name:
            continue
        deal, created = upsert_deal_from_event(company, event, target_name)
        counters["deals_created" if created else "deals_updated"] += 1
        stage_event, event_created = AcquisitionLifecycleEvent.objects.update_or_create(
            deal=deal,
            stage=deal.current_stage,
            title=(event.actual_change or event.source_claim or event.decision or event.get_event_type_display())[:512],
            event_date=event.event_date,
            defaults={
                "description": event.actual_change or event.after_state or event.decision,
                "evidence_text": event.evidence_text or event.source_claim,
                "source_document": event.source_document,
                "confidence_score": event.confidence_score,
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        counters["events_created" if event_created else "events_updated"] += 1

    if not AcquisitionLifecycleDeal.objects.filter(company=company).exists():
        for target_name in fallback_targets[:4]:
            deal, created = upsert_profile_deal(company, target_name, effective_date, source)
            counters["deals_created" if created else "deals_updated"] += 1
            stage_event, event_created = AcquisitionLifecycleEvent.objects.update_or_create(
                deal=deal,
                stage=AcquisitionStage.INTEGRATED,
                title=f"{target_name} listed in reviewed company profile",
                event_date=effective_date,
                defaults={
                    "description": f"{target_name} appears in reviewed Company 360 subsidiary, brand, or segment context.",
                    "evidence_text": f"Reviewed Company 360 profile lists {target_name} in company structure or portfolio context.",
                    "source_document": source,
                    "confidence_score": "0.700",
                    "review_status": PromiseReviewStatus.REVIEWED,
                },
            )
            counters["events_created" if event_created else "events_updated"] += 1

    link_strategic_turns(company)
    return counters


def acquisition_lifecycle_quality_issues(company: Company) -> list[str]:
    deals = AcquisitionLifecycleDeal.objects.filter(company=company, review_status=PromiseReviewStatus.REVIEWED)
    if not deals.exists():
        return ["no reviewed acquisition lifecycle deals"]
    issues = []
    if not deals.filter(stage_events__isnull=False).exists():
        issues.append("no reviewed lifecycle stage events")
    if not deals.exclude(management_rationale="").exists():
        issues.append("management rationale unavailable")
    if not deals.exclude(outcome_review="").exists():
        issues.append("outcome review unavailable")
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


def acquisition_events(company: Company) -> list[BusinessEvent]:
    return list(
        BusinessEvent.objects.filter(company=company)
        .filter(
            event_type="ACQUISITION"
        )
        .select_related("source_document")
        .order_by("-event_date", "-created_at")[:40]
    )


def upsert_deal_from_event(company: Company, event: BusinessEvent, target_name: str) -> tuple[AcquisitionLifecycleDeal, bool]:
    text = event_text(event)
    stage = stage_for_text(text)
    outcome = outcome_for_stage_text(stage, text)
    transaction_type = transaction_type_for_text(text)
    deal, created = AcquisitionLifecycleDeal.objects.update_or_create(
        company=company,
        slug=slugify(target_name)[:255] or f"acquisition-{event.id}",
        defaults={
            "target_name": target_name[:255],
            "target_company": match_company(target_name),
            "transaction_type": transaction_type,
            "current_stage": stage,
            "outcome_category": outcome,
            "announcement_date": event.event_date,
            "close_date": event.event_date if stage in {AcquisitionStage.CLOSED, AcquisitionStage.INTEGRATING, AcquisitionStage.INTEGRATED, AcquisitionStage.OUTCOME_REVIEWED} else None,
            "currency": "",
            "payment_form": "",
            "approvals": [],
            "conditions": [],
            "management_rationale": event.decision or event.trigger,
            "promised_synergies": synergy_text(event),
            "integration_summary": integration_text(event),
            "outcome_review": event.outcome if outcome != AcquisitionOutcomeCategory.TOO_EARLY else "",
            "source_document": event.source_document,
            "linked_event": event,
            "confidence_score": event.confidence_score,
            "review_status": PromiseReviewStatus.REVIEWED,
            "is_published": True,
        },
    )
    return deal, created


def upsert_profile_deal(
    company: Company,
    target_name: str,
    effective_date: date,
    source: SourceDocument | None,
) -> tuple[AcquisitionLifecycleDeal, bool]:
    deal, created = AcquisitionLifecycleDeal.objects.update_or_create(
        company=company,
        slug=slugify(target_name)[:255],
        defaults={
            "target_name": target_name[:255],
            "target_company": match_company(target_name),
            "transaction_type": AcquisitionTransactionType.ACQUISITION,
            "current_stage": AcquisitionStage.INTEGRATED,
            "outcome_category": AcquisitionOutcomeCategory.VALUE_UNCLEAR,
            "announcement_date": None,
            "close_date": None,
            "currency": "",
            "payment_form": "",
            "approvals": [],
            "conditions": [],
            "management_rationale": f"{target_name} is included in the reviewed Company 360 company structure or portfolio context.",
            "promised_synergies": "",
            "integration_summary": f"{target_name} is part of the current reviewed company portfolio; original integration milestones are not yet reviewed.",
            "outcome_review": "Outcome is not classified beyond current portfolio inclusion because original deal terms and post-close evidence have not been reviewed.",
            "source_document": source,
            "confidence_score": "0.700",
            "review_status": PromiseReviewStatus.REVIEWED,
            "is_published": True,
        },
    )
    return deal, created


def profile_targets(company: Company, profile: CompanyProfileSnapshot | None) -> list[str]:
    fallback = PROFILE_FALLBACKS.get(company.slug, {})
    values: list[str] = []
    profile_values = getattr(profile, "subsidiaries", []) if profile else []
    source_values = profile_values if isinstance(profile_values, list) and profile_values else fallback.get("subsidiaries", [])
    for item in source_values if isinstance(source_values, list) else []:
        label = clean_label(str(item))
        if label and normalize_key(label) != normalize_key(company.name):
            values.append(label)
    seen = set()
    unique = []
    for value in values:
        key = normalize_key(value)
        if key in seen:
            continue
        seen.add(key)
        unique.append(value)
    return unique


def link_strategic_turns(company: Company) -> None:
    turns = StrategicTurn.objects.filter(company=company, turn_type="ACQUISITION").order_by("-start_date", "-created_at")
    for deal in AcquisitionLifecycleDeal.objects.filter(company=company, linked_strategic_turn__isnull=True):
        match = next((turn for turn in turns if normalize_key(deal.target_name) in normalize_key(turn.title + " " + turn.summary)), None)
        if match:
            deal.linked_strategic_turn = match
            deal.save(update_fields=["linked_strategic_turn", "updated_at"])


def target_from_event(event: BusinessEvent) -> str:
    text = clean_label(event.actual_change or event.source_claim or event.decision or event.after_state or "Acquisition activity")
    if is_generic_acquisition_summary(text):
        return ""
    patterns = [
        r"acquisition of ([A-Z][A-Za-z0-9&.,' -]{2,80})",
        r"acquired ([A-Z][A-Za-z0-9&.,' -]{2,80})",
        r"merger with ([A-Z][A-Za-z0-9&.,' -]{2,80})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return clean_label(match.group(1).split(" for ")[0].split(" from ")[0].split(" and ")[0])
    return text[:80] or "Acquisition activity"


def purge_generic_event_deals(company: Company) -> None:
    generic_deals = [
        deal.id
        for deal in AcquisitionLifecycleDeal.objects.filter(company=company, linked_event__isnull=False)
        if is_generic_acquisition_summary(deal.target_name)
    ]
    if generic_deals:
        AcquisitionLifecycleDeal.objects.filter(id__in=generic_deals).delete()


def purge_profile_deals_not_in_targets(company: Company, targets: list[str]) -> None:
    target_keys = {normalize_key(target) for target in targets}
    stale_ids = [
        deal.id
        for deal in AcquisitionLifecycleDeal.objects.filter(company=company, linked_event__isnull=True)
        if normalize_key(deal.target_name) not in target_keys
    ]
    if stale_ids:
        AcquisitionLifecycleDeal.objects.filter(id__in=stale_ids).delete()


def is_generic_acquisition_summary(text: str) -> bool:
    lowered = text.lower()
    generic_phrases = (
        "used acquisitions, mergers, or divestitures to reshape",
        "uses acquisitions and divestitures",
        "acquisition activity",
    )
    return any(phrase in lowered for phrase in generic_phrases)


def event_text(event: BusinessEvent) -> str:
    return " ".join([event.source_claim or "", event.actual_change or "", event.decision or "", event.outcome or "", event.evidence_text or ""]).lower()


def stage_for_text(text: str) -> str:
    if any(term in text for term in IMPAIRMENT_TERMS):
        return AcquisitionStage.IMPAIRED_WRITTEN_DOWN
    if any(term in text for term in DIVESTITURE_TERMS):
        return AcquisitionStage.DIVESTED
    if "abandon" in text or "blocked" in text:
        return AcquisitionStage.BLOCKED_ABANDONED
    if "integrat" in text:
        return AcquisitionStage.INTEGRATING
    if "closed" in text or "completed" in text:
        return AcquisitionStage.CLOSED
    if "approved" in text:
        return AcquisitionStage.APPROVED
    if "review" in text or "regulatory" in text:
        return AcquisitionStage.UNDER_REVIEW
    return AcquisitionStage.ANNOUNCED


def outcome_for_stage_text(stage: str, text: str) -> str:
    if stage == AcquisitionStage.BLOCKED_ABANDONED:
        return AcquisitionOutcomeCategory.ABANDONED
    if stage == AcquisitionStage.DIVESTED:
        return AcquisitionOutcomeCategory.DIVESTED
    if stage == AcquisitionStage.IMPAIRED_WRITTEN_DOWN:
        return AcquisitionOutcomeCategory.IMPAIRED
    if "delay" in text:
        return AcquisitionOutcomeCategory.DELAYED
    if stage in {AcquisitionStage.INTEGRATING, AcquisitionStage.CLOSED, AcquisitionStage.APPROVED, AcquisitionStage.UNDER_REVIEW, AcquisitionStage.ANNOUNCED}:
        return AcquisitionOutcomeCategory.TOO_EARLY
    return AcquisitionOutcomeCategory.VALUE_UNCLEAR


def transaction_type_for_text(text: str) -> str:
    if any(term in text for term in DIVESTITURE_TERMS):
        return AcquisitionTransactionType.DIVESTITURE
    if "joint venture" in text:
        return AcquisitionTransactionType.JOINT_VENTURE
    if "minority" in text or "investment" in text:
        return AcquisitionTransactionType.MINORITY_INVESTMENT
    if "merger" in text:
        return AcquisitionTransactionType.MERGER
    if "asset" in text:
        return AcquisitionTransactionType.ASSET_PURCHASE
    return AcquisitionTransactionType.ACQUISITION


def synergy_text(event: BusinessEvent) -> str:
    text = " ".join([event.decision or "", event.source_claim or "", event.evidence_text or ""])
    return text if "synerg" in text.lower() or "cost saving" in text.lower() else ""


def integration_text(event: BusinessEvent) -> str:
    text = " ".join([event.after_state or "", event.actual_change or "", event.outcome or ""])
    return text if "integrat" in text.lower() else ""


def match_company(name: str) -> Company | None:
    key = normalize_key(name)
    for company in Company.objects.filter(is_active=True):
        names = [company.name, company.slug, *(company.aliases if isinstance(company.aliases, list) else [])]
        if any(normalize_key(str(row)) == key for row in names):
            return company
    return None


def clean_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\n", " ")).strip(" .;:-")


def normalize_key(value: str) -> str:
    return slugify(value).replace("-", "")
