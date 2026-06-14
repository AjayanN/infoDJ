from __future__ import annotations

import re
from dataclasses import dataclass

from django.utils.text import slugify

from apps.companies.models import (
    ManagementPromise,
    PromiseReviewStatus,
    PromiseStatus,
    PromiseType,
)
from apps.ingestion.models import ArticleExtraction


@dataclass(frozen=True)
class ReviewedPromiseSpec:
    title: str
    evidence_pattern: str
    scope: str
    promise_type: str = PromiseType.STRATEGIC_CLAIM
    current_status: str = PromiseStatus.IN_PROGRESS


# These patterns identify statements that were manually selected from each company's
# stored annual filing. The exact filing sentence, not this configuration, is published.
REVIEWED_PROMISE_SPECS: dict[str, ReviewedPromiseSpec] = {
    "apple": ReviewedPromiseSpec(
        "Maintain a safe and secure workplace",
        r"Company is committed to the safety and security of its team members",
        "Global workforce",
        PromiseType.COMMITMENT,
    ),
    "microsoft": ReviewedPromiseSpec(
        "Continue investing in cloud and AI infrastructure",
        r"continue to invest in high performance and sustainable computing",
        "Cloud computing, AI infrastructure and datacenters",
    ),
    "jpmorgan-chase": ReviewedPromiseSpec(
        "Maintain a fortress balance sheet",
        r"fortress balance sheet",
        "Firm-wide capital, liquidity and risk management",
    ),
    "visa": ReviewedPromiseSpec(
        "Provide a single connection point for money movement",
        r"aim to provide a single connection point",
        "Businesses, governments and consumers",
        PromiseType.ASPIRATION,
    ),
    "unitedhealth-group": ReviewedPromiseSpec(
        "Advance whole-person health",
        r"seek to advance whole-person health",
        "UnitedHealth Group care and technology businesses",
        PromiseType.ASPIRATION,
    ),
    "pfizer": ReviewedPromiseSpec(
        "Advance the product pipeline and existing products",
        r"committed to strategically capitalizing on growth opportunities",
        "Product pipeline, existing products and business development",
        PromiseType.COMMITMENT,
    ),
    "amazon": ReviewedPromiseSpec(
        "Further expand internationally",
        r"plan to further expand internationally",
        "International operations",
        PromiseType.COMMITMENT,
    ),
    "walmart": ReviewedPromiseSpec(
        "Continue investing in omnichannel and ecommerce",
        r"continue to heavily invest in omni-channel and eCommerce innovation",
        "Global omnichannel and ecommerce operations",
    ),
    "exxonmobil": ReviewedPromiseSpec(
        "Direct investment toward energy-transition opportunities",
        r"strategy for the energy transition will also depend on our ability",
        "Energy-transition technologies and businesses",
    ),
    "nextera-energy": ReviewedPromiseSpec(
        "Place additional solar and battery storage capacity in service during 2026",
        r"expects to place an additional 298 MW of solar capacity and approximately 1,420 MW",
        "Florida Power & Light solar generation and battery storage",
        PromiseType.GUIDANCE,
    ),
    "ford-motor-company": ReviewedPromiseSpec(
        "Help build a better world through freedom of movement",
        r"Company is committed to helping build a better world",
        "Global automotive operations and workforce",
        PromiseType.COMMITMENT,
    ),
    "tesla": ReviewedPromiseSpec(
        "Leverage vehicle and energy operations toward the company objective",
        r"intend to leverage our current operations",
        "Electric vehicles, energy generation, storage, software and services",
    ),
    "caterpillar": ReviewedPromiseSpec(
        "Support long-term profitable growth with an inclusive workforce",
        r"contribute to our strategy for long-term profitable growth",
        "Global workforce and operating strategy",
    ),
    "general-electric": ReviewedPromiseSpec(
        "Invest in technologies for a more sustainable future of flight",
        r"committed to investing in developing and maturing technologies",
        "GE Aerospace technology portfolio",
        PromiseType.COMMITMENT,
    ),
    "disney": ReviewedPromiseSpec(
        "Launch an ESPN-branded tile on Disney+ in the United States",
        r"plans to launch an ESPN branded tile on Disney\+",
        "Disney+ in the United States",
        PromiseType.COMMITMENT,
    ),
    "netflix": ReviewedPromiseSpec(
        "Offer a range of pricing plans including an ad-supported plan",
        r"aim to offer a range of pricing plans",
        "Global subscription plans",
        PromiseType.ASPIRATION,
    ),
    "prologis": ReviewedPromiseSpec(
        "Grow the strategic capital business",
        r"plan to grow this business and increase revenues",
        "Strategic capital ventures and assets under management",
        PromiseType.COMMITMENT,
    ),
    "american-tower": ReviewedPromiseSpec(
        "Increase utilization of existing communications sites",
        r"continue to target our sales and marketing activities to increase the utilization",
        "Existing communications sites",
    ),
    "freeport-mcmoran": ReviewedPromiseSpec(
        "Target 300 million pounds of annual copper production",
        r"targeting annual production of 300 million pounds of copper in 2026",
        "Operational improvement initiatives",
        PromiseType.TARGET,
    ),
    "newmont": ReviewedPromiseSpec(
        "Reduce emissions by 2030 and pursue carbon neutrality by 2050",
        r"GHG emissions reduction targets of 32% for Scope 1 and Scope 2",
        "Scope 1, Scope 2 and Scope 3 greenhouse-gas emissions",
        PromiseType.TARGET,
    ),
}


def build_reviewed_management_promise(company) -> dict[str, int | str]:
    spec = REVIEWED_PROMISE_SPECS.get(company.slug)
    if spec is None:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "no reviewed specification"}

    extractions = (
        ArticleExtraction.objects.filter(
            source_document__company=company,
            source_document__title__icontains="10-K",
            extraction_status="SUCCEEDED",
        )
        .exclude(clean_text="")
        .select_related("source_document")
        .order_by("-source_document__published_date", "-word_count", "-updated_at")
    )
    if not extractions.exists():
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "no extracted 10-K"}

    matched = next(
        (
            (extraction, statement)
            for extraction in extractions
            if (statement := _matching_sentence(extraction.clean_text, spec.evidence_pattern))
        ),
        None,
    )
    if matched is None:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "reviewed statement not found"}
    extraction, statement = matched

    statement_date = (
        extraction.source_document.published_date.date()
        if extraction.source_document.published_date
        else extraction.updated_at.date()
    )
    promise, created = ManagementPromise.objects.update_or_create(
        company=company,
        slug=slugify(spec.title),
        defaults={
            "title": spec.title,
            "promise_type": spec.promise_type,
            "original_statement": statement,
            "speaker": f"{company.name} management",
            "speaker_role": "Company management",
            "statement_date": statement_date,
            "scope": spec.scope,
            "evaluation_rule": (
                "Monitor subsequent reviewed filings and company disclosures for concrete actions, "
                "continued reporting, revision, withdrawal, or evidence that this strategic statement was fulfilled."
            ),
            "current_status": spec.current_status,
            "source_document": extraction.source_document,
            "evidence_text": statement,
            "confidence_score": "0.900",
            "review_status": PromiseReviewStatus.REVIEWED,
            "is_published": True,
        },
    )
    return {"created": int(created), "updated": int(not created), "skipped": 0, "reason": ""}


def management_promise_quality_issues(company) -> list[str]:
    promises = company.management_promises.filter(
        is_published=True,
        review_status=PromiseReviewStatus.REVIEWED,
    ).select_related("source_document")
    if not promises.exists():
        return ["no reviewed published management promise"]

    issues = []
    for promise in promises:
        prefix = promise.slug
        if promise.source_document is None:
            issues.append(f"{prefix}: source document unavailable")
        if not promise.original_statement.strip() or not promise.evidence_text.strip():
            issues.append(f"{prefix}: filing statement or evidence unavailable")
        if not promise.evaluation_rule.strip():
            issues.append(f"{prefix}: evaluation rule unavailable")
    return issues


def _matching_sentence(text: str, pattern: str) -> str:
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        normalized = " ".join(sentence.split())
        if re.search(pattern, normalized, re.IGNORECASE):
            return normalized[:4000]
    return ""
