from __future__ import annotations

from dataclasses import dataclass

from django.utils.text import slugify

from apps.companies.models import (
    MilestoneOrigin,
    MilestoneStatus,
    MilestoneType,
    PromiseReviewStatus,
    PromiseStatus,
    StrategyMilestone,
    StrategyMilestoneStatusUpdate,
)


@dataclass(frozen=True)
class ReviewedMilestoneSpec:
    milestone_type: str
    success_condition: str
    related_entities: tuple[dict[str, str], ...] = ()


REVIEWED_MILESTONE_SPECS: dict[str, ReviewedMilestoneSpec] = {
    "apple": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Subsequent reviewed company evidence confirms continued workplace safety and security actions."),
    "microsoft": ReviewedMilestoneSpec(MilestoneType.CAPACITY_TARGET, "Reviewed disclosures confirm continued cloud and AI infrastructure investment or capacity deployment."),
    "jpmorgan-chase": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Reviewed capital, liquidity, and risk disclosures continue to support the fortress balance-sheet commitment."),
    "visa": ReviewedMilestoneSpec(MilestoneType.PRODUCT_ADOPTION, "Reviewed product evidence shows customers can use a unified Visa connection for additional money-movement use cases."),
    "unitedhealth-group": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Reviewed operating evidence identifies concrete whole-person health delivery actions or outcomes."),
    "pfizer": ReviewedMilestoneSpec(MilestoneType.REGULATORY_APPROVAL, "Reviewed pipeline disclosures show a named development, approval, or launch step for pipeline or acquired products."),
    "amazon": ReviewedMilestoneSpec(MilestoneType.MARKET_ENTRY, "Reviewed company disclosures confirm entry into or material expansion within an additional international market."),
    "walmart": ReviewedMilestoneSpec(MilestoneType.PRODUCT_ADOPTION, "Reviewed disclosures confirm continued omnichannel or ecommerce deployment and customer adoption."),
    "exxonmobil": ReviewedMilestoneSpec(MilestoneType.CAPACITY_TARGET, "Reviewed disclosures identify completed investment or operating capacity in an energy-transition business."),
    "nextera-energy": ReviewedMilestoneSpec(MilestoneType.CAPACITY_TARGET, "Place the announced 298 MW of solar and approximately 1,420 MW of battery storage capacity in service during 2026."),
    "ford-motor-company": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Reviewed company evidence identifies a completed product, workforce, or community action tied to freedom of movement."),
    "tesla": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Reviewed disclosures connect vehicle and energy operations to a concrete delivered company objective."),
    "caterpillar": ReviewedMilestoneSpec(MilestoneType.STRATEGIC_EXECUTION, "Reviewed workforce or operating evidence demonstrates an action supporting long-term profitable growth."),
    "general-electric": ReviewedMilestoneSpec(MilestoneType.PRODUCT_ADOPTION, "Reviewed disclosures identify a completed sustainable-flight technology test, certification, or customer deployment."),
    "disney": ReviewedMilestoneSpec(MilestoneType.LAUNCH, "Launch the ESPN-branded tile on Disney+ in the United States."),
    "netflix": ReviewedMilestoneSpec(MilestoneType.LAUNCH, "Launch Basic with Ads in the 12 announced countries."),
    "prologis": ReviewedMilestoneSpec(MilestoneType.PARTNERSHIP, "Reviewed disclosures show additional strategic-capital partnerships, assets under management, or related revenue growth."),
    "american-tower": ReviewedMilestoneSpec(MilestoneType.PRODUCT_ADOPTION, "Reviewed tenant-billing or colocations evidence confirms increased utilization of existing communications sites."),
    "freeport-mcmoran": ReviewedMilestoneSpec(MilestoneType.CAPACITY_TARGET, "Deliver approximately 300 million pounds of annual copper production from the identified operational initiatives."),
    "newmont": ReviewedMilestoneSpec(MilestoneType.CAPACITY_TARGET, "Report progress against the stated 2030 emissions-reduction targets using comparable reviewed measures."),
}


PROMISE_TO_MILESTONE_STATUS = {
    PromiseStatus.ANNOUNCED: MilestoneStatus.EXPECTED,
    PromiseStatus.IN_PROGRESS: MilestoneStatus.STARTED,
    PromiseStatus.ACHIEVED: MilestoneStatus.COMPLETED,
    PromiseStatus.PARTIALLY_ACHIEVED: MilestoneStatus.STARTED,
    PromiseStatus.MISSED: MilestoneStatus.FAILED,
    PromiseStatus.DELAYED: MilestoneStatus.DELAYED,
    PromiseStatus.REVISED: MilestoneStatus.CHANGED,
    PromiseStatus.WITHDRAWN: MilestoneStatus.CANCELLED,
    PromiseStatus.NO_LONGER_DISCLOSED: MilestoneStatus.UNKNOWN,
    PromiseStatus.TOO_EARLY: MilestoneStatus.EXPECTED,
    PromiseStatus.UNVERIFIABLE: MilestoneStatus.UNKNOWN,
}


def build_reviewed_strategy_milestone(company) -> dict[str, int | str]:
    spec = REVIEWED_MILESTONE_SPECS.get(company.slug)
    if spec is None:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "no reviewed milestone specification"}
    promises = company.management_promises.filter(
        is_published=True,
        review_status=PromiseReviewStatus.REVIEWED,
    ).select_related("source_document", "linked_kpi", "linked_strategic_turn")
    promise = promises.filter(current_status=PromiseStatus.ACHIEVED).first() or promises.order_by("-statement_date").first()
    if promise is None or promise.source_document is None or not promise.evidence_text.strip():
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "reviewed source-backed promise unavailable"}

    status = PROMISE_TO_MILESTONE_STATUS.get(promise.current_status, MilestoneStatus.UNKNOWN)
    milestone, created = StrategyMilestone.objects.update_or_create(
        company=company,
        slug=slugify(promise.title),
        defaults={
            "title": promise.title,
            "milestone_type": spec.milestone_type,
            "origin": MilestoneOrigin.MANAGEMENT,
            "current_status": status,
            "expected_start_date": promise.target_start_date,
            "expected_end_date": promise.target_end_date,
            "date_precision": "EXACT" if promise.target_end_date else "UNKNOWN",
            "owner": promise.speaker or f"{company.name} management",
            "success_condition": spec.success_condition,
            "blocker": "",
            "outcome_review": _outcome_review(status),
            "source_document": promise.source_document,
            "evidence_text": promise.evidence_text,
            "linked_promise": promise,
            "linked_kpi": promise.linked_kpi,
            "linked_strategic_turn": promise.linked_strategic_turn,
            "related_entities": list(spec.related_entities),
            "confidence_score": "0.900",
            "review_status": PromiseReviewStatus.REVIEWED,
            "is_published": True,
        },
    )
    kept_update_ids = []
    base_update, _created = StrategyMilestoneStatusUpdate.objects.update_or_create(
        milestone=milestone,
        status_date=promise.statement_date,
        status=MilestoneStatus.EXPECTED if status == MilestoneStatus.COMPLETED else status,
        source_document=promise.source_document,
        defaults={
            "summary": _status_summary(milestone, MilestoneStatus.EXPECTED if status == MilestoneStatus.COMPLETED else status),
            "blocker": "",
            "evidence_text": promise.evidence_text,
            "confidence_score": "0.900",
            "review_status": PromiseReviewStatus.REVIEWED,
        },
    )
    kept_update_ids.append(base_update.id)
    for update in promise.updates.filter(review_status=PromiseReviewStatus.REVIEWED).select_related("source_document"):
        update_status = PROMISE_TO_MILESTONE_STATUS.get(update.status, MilestoneStatus.UNKNOWN)
        status_update, _created = StrategyMilestoneStatusUpdate.objects.update_or_create(
            milestone=milestone,
            status_date=update.update_date,
            status=update_status,
            source_document=update.source_document or promise.source_document,
            defaults={
                "summary": update.summary or _status_summary(milestone, update_status),
                "blocker": update.contradiction_note if update.is_contradiction_candidate else "",
                "evidence_text": update.evidence_text or promise.evidence_text,
                "confidence_score": update.confidence_score or "0.900",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        kept_update_ids.append(status_update.id)
    milestone.status_updates.exclude(id__in=kept_update_ids).delete()
    return {"created": int(created), "updated": int(not created), "skipped": 0, "reason": ""}


def strategy_milestone_quality_issues(company) -> list[str]:
    milestones = company.strategy_milestones.filter(
        is_published=True,
        review_status=PromiseReviewStatus.REVIEWED,
    ).select_related("source_document", "linked_promise")
    if not milestones.exists():
        return ["no reviewed published strategy milestone"]
    issues = []
    for milestone in milestones:
        prefix = milestone.slug
        if not milestone.evidence_text.strip() or not milestone.success_condition.strip():
            issues.append(f"{prefix}: evidence or success condition unavailable")
        if milestone.source_document_id is None:
            issues.append(f"{prefix}: source document unavailable")
        if milestone.origin == MilestoneOrigin.ANALYST_INFERRED and milestone.review_status != PromiseReviewStatus.REVIEWED:
            issues.append(f"{prefix}: inferred milestone is not reviewed")
        if not milestone.status_updates.filter(review_status=PromiseReviewStatus.REVIEWED).exists():
            issues.append(f"{prefix}: reviewed status history unavailable")
    return issues


def _status_summary(milestone: StrategyMilestone, status: str) -> str:
    labels = {
        MilestoneStatus.EXPECTED: "Management announced the milestone; execution has not yet been confirmed.",
        MilestoneStatus.STARTED: "Management's reviewed statement indicates this milestone is in progress.",
        MilestoneStatus.COMPLETED: "Reviewed evidence records this milestone as completed.",
        MilestoneStatus.DELAYED: "Reviewed evidence records the milestone as delayed.",
        MilestoneStatus.CHANGED: "Reviewed evidence records a changed milestone or success condition.",
        MilestoneStatus.CANCELLED: "Reviewed evidence records the milestone as cancelled.",
        MilestoneStatus.FAILED: "Reviewed evidence records the milestone as failed or missed.",
        MilestoneStatus.UNKNOWN: "Current milestone progress cannot be verified from reviewed evidence.",
    }
    return f"{milestone.title}: {labels[status]}"


def _outcome_review(status: str) -> str:
    if status == MilestoneStatus.COMPLETED:
        return "The announced execution step was completed according to reviewed company evidence."
    return "Outcome remains open until a subsequent reviewed source confirms completion, change, delay, cancellation, or failure."
