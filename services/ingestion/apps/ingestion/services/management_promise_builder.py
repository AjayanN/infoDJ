from __future__ import annotations

from django.utils.text import slugify

from apps.companies.models import KpiTarget, ManagementPromise, PromiseReviewStatus, PromiseStatus, PromiseType


def build_promise_candidates_from_kpi_targets(company) -> dict[str, int]:
    counters = {"created": 0, "updated": 0, "skipped": 0}
    targets = KpiTarget.objects.filter(kpi__company=company).select_related("kpi", "source_document")
    for target in targets:
        if target.source_document is None:
            counters["skipped"] += 1
            continue
        title = f"{target.kpi.name} target for {target.target_date.isoformat()}"
        promise, created = ManagementPromise.objects.update_or_create(
            company=company,
            slug=slugify(f"{target.kpi.slug}-{target.target_date.isoformat()}"),
            defaults={
                "title": title,
                "promise_type": PromiseType.TARGET,
                "original_statement": target.condition or title,
                "statement_date": target.source_document.published_date.date()
                if target.source_document.published_date else target.target_date,
                "target_end_date": target.target_date,
                "metric_name": target.kpi.name,
                "target_value": target.target_value,
                "unit": target.kpi.unit,
                "scope": target.kpi.scope,
                "conditions": target.condition,
                "evaluation_rule": (
                    f"Compare the latest reviewed {target.kpi.name} observation at or before "
                    f"{target.target_date.isoformat()} with {target.target_value} {target.kpi.unit}."
                ),
                "current_status": target.status if target.status in PromiseStatus.values else PromiseStatus.ANNOUNCED,
                "source_document": target.source_document,
                "evidence_text": target.condition,
                "linked_kpi": target.kpi,
                "confidence_score": "0.700",
                "review_status": PromiseReviewStatus.NEEDS_REVIEW,
                "is_published": False,
            },
        )
        counters["created" if created else "updated"] += 1
    return counters
