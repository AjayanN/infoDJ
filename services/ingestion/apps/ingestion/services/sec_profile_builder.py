from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from apps.companies.models import CompanyProfileSnapshot, CompanyProfileStatus
from apps.curation.models import BusinessEvent
from apps.ingestion.models import ArticleExtraction
from apps.ingestion.services.company_profile_fallbacks import PROFILE_FALLBACKS


@dataclass(frozen=True)
class SecProfileData:
    business_model: str
    subsidiaries: tuple[str, ...]
    brands: tuple[str, ...]
    segments: tuple[str, ...]
    products: tuple[str, ...]
    customer_groups: tuple[str, ...]
    revenue_sources: tuple[str, ...]
    leadership: tuple[str, ...]
    competitors: tuple[str, ...]
    strategic_priorities: tuple[str, ...]
    evidence_text: str


def build_sec_company_profile(company) -> CompanyProfileSnapshot:
    extraction = (
        ArticleExtraction.objects.filter(
            source_document__company=company,
            source_document__title__icontains="10-K",
            extraction_status="SUCCEEDED",
        )
        .exclude(clean_text="")
        .select_related("source_document")
        .order_by("-word_count", "-source_document__published_date", "-updated_at")
        .first()
    )
    if extraction is None:
        raise ValueError(f"{company.name} has no successful 10-K extraction")

    priorities = tuple(
        unique_values(
            BusinessEvent.objects.filter(company=company)
            .exclude(actual_change="")
            .order_by("-event_date", "-created_at")
            .values_list("actual_change", flat=True)[:5]
        )
    )
    data = parse_sec_profile_text(extraction.clean_text, company.name, priorities=priorities)
    data = apply_profile_fallbacks(data, company.slug)
    effective_date = extraction.source_document.published_date or date.today()
    snapshot, _created = CompanyProfileSnapshot.objects.update_or_create(
        company=company,
        effective_date=effective_date,
        source_document=extraction.source_document,
        defaults={
            "status": CompanyProfileStatus.REVIEWED,
            "business_model": data.business_model,
            "subsidiaries": list(data.subsidiaries),
            "brands": list(data.brands),
            "segments": list(data.segments),
            "products": list(data.products),
            "customer_groups": list(data.customer_groups),
            "revenue_sources": list(data.revenue_sources),
            "leadership": list(data.leadership),
            "competitors": list(data.competitors),
            "strategic_priorities": list(data.strategic_priorities),
            "evidence_text": data.evidence_text,
            "confidence_score": "0.750",
        },
    )
    return snapshot


def apply_profile_fallbacks(data: SecProfileData, company_slug: str) -> SecProfileData:
    fallback = PROFILE_FALLBACKS.get(company_slug, {})
    values = {}
    for field in SecProfileData.__dataclass_fields__:
        current = getattr(data, field)
        replacement = fallback.get(field)
        if current or replacement is None:
            values[field] = current
        elif field in {"business_model", "evidence_text"}:
            values[field] = str(replacement)
        else:
            values[field] = tuple(replacement)
    return SecProfileData(**values)


def parse_sec_profile_text(text: str, company_name: str, *, priorities: tuple[str, ...] = ()) -> SecProfileData:
    normalized = " ".join(text.split())
    business = section_between(normalized, r"ITEM\s+1\.?\s+Business", r"ITEM\s+1A\.?\s+Risk Factors")
    if not business:
        business = normalized[:30000]

    segments = extract_segments(business)
    revenue_sources = extract_revenue_sources(business)
    products = extract_business_labels(business)
    customers = extract_customer_groups(business)
    subsidiaries = extract_owned_businesses(business)
    leadership = extract_leadership(normalized)
    competitors = extract_competition_context(business)
    brands = extract_brands(business, products)
    business_model = business_model_summary(business, company_name, segments, revenue_sources)
    evidence = business[:1800]
    return SecProfileData(
        business_model=business_model,
        subsidiaries=tuple(subsidiaries),
        brands=tuple(brands),
        segments=tuple(segments),
        products=tuple(products),
        customer_groups=tuple(customers),
        revenue_sources=tuple(revenue_sources),
        leadership=tuple(leadership),
        competitors=tuple(competitors),
        strategic_priorities=priorities,
        evidence_text=evidence,
    )


def section_between(text: str, start_pattern: str, end_pattern: str) -> str:
    candidates = []
    for start in re.finditer(start_pattern, text, re.IGNORECASE):
        end = re.search(end_pattern, text[start.end() :], re.IGNORECASE)
        section = text[start.end() : start.end() + end.start()] if end else text[start.end() : start.end() + 30000]
        if len(section) <= 30000:
            candidates.append(section)
    return max(candidates, key=len, default="")


def extract_segments(text: str) -> list[str]:
    patterns = (
        r"operations? in (?:the following )?(?:\w+ )?segments?:\s*([^\.]{3,240})",
        r"reportable segments? (?:are|include|consist of)\s*([^\.]{3,240})",
        r"business segments? (?:are|include|consist of)\s*([^\.]{3,240})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            values = split_named_list(match.group(1))
            if values:
                return values[:10]
    return extract_heading_labels(text, limit=6)


def extract_revenue_sources(text: str) -> list[str]:
    values = []
    for match in re.finditer(r"•\s*([^•]{2,70}?)\s+-\s+(?:Fees|Sales|Rentals|Revenues|Revenue|Amounts)", text):
        values.append(clean_label(match.group(1)))
    if not values:
        for phrase in ("subscription fees", "advertising", "affiliate fees", "product sales", "service revenue", "licensing fees", "rental income", "interest income"):
            if re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE):
                values.append(phrase.title())
    return unique_values(values)[:12]


def extract_business_labels(text: str) -> list[str]:
    values = []
    for match in re.finditer(r"[•◦]\s*([A-Z][A-Za-z0-9+&'/. -]{2,55})(?=\s*(?::| -|\u2014|◦))", text[:22000]):
        label = clean_label(match.group(1))
        if is_useful_label(label):
            values.append(label)
    for match in re.finditer(
        r"\b([A-Z][A-Za-z0-9+&' -]{1,40})(?:®|™)?\s+is (?:the|a) Company[’']s (?:line|service|platform|offering)",
        text[:22000],
    ):
        values.append(clean_label(match.group(1)))
    for match in re.finditer(r"Products and Services\s+(.{20,1200}?)(?:Customers|Competition|Seasonality|Employees)", text[:22000], re.IGNORECASE):
        values.extend(re.findall(r"\b([A-Z][A-Za-z0-9+.-]{2,30})(?:®|™)?\b", match.group(1)))
    return unique_values(values)[:18]


def extract_customer_groups(text: str) -> list[str]:
    values = []
    patterns = (
        r"fees charged to ([^.;]{3,100})",
        r"sales? to ([^.;]{3,100})",
        r"customers include ([^.;]{3,160})",
        r"serve(?:s|d)? ([^.;]{3,120}) customers",
        r"serve ([^.;]{3,180}) through",
        r"customers (?:are|include|consist of) ([^.;]{3,180})",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            values.extend(split_named_list(match.group(1)))
    return unique_values(values)[:12]


def extract_owned_businesses(text: str) -> list[str]:
    values = []
    patterns = (
        r"(?:equity investment|ownership interest) in ([A-Z][A-Za-z0-9+&'/ -]{2,70})(?=\.|,|;|\(|$)",
        r"owned \d+% by the Company\) branded ([A-Z][A-Za-z0-9+&'/ -]{2,70})(?=\.|,|;|\(|$)",
    )
    for pattern in patterns:
        values.extend(clean_label(match.group(1)) for match in re.finditer(pattern, text))
    return unique_values(values)[:12]


def extract_leadership(text: str) -> list[str]:
    values = []
    for match in re.finditer(
        r"([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})\s*\|\s*\d{2}\s*\|\s*([^|]{3,100}?)(?:\(\d+\))?\s*\|",
        text,
    ):
        title = clean_label(match.group(2))
        if "Officer" in title or "President" in title:
            values.append(f"{match.group(1)}, {title}")
    for match in re.finditer(
        r"([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}),?\s+(?:our\s+)?((?:President and )?Chief Executive Officer|Chief Financial Officer|Chief Operating Officer)",
        text,
    ):
        values.append(f"{match.group(1)}, {match.group(2)}")
    return unique_values(values)[:8]


def extract_competition_context(text: str) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    values = [sentence for sentence in sentences if re.search(r"\bcompete|\bcompetition", sentence, re.IGNORECASE)]
    return unique_values(sentence[:360] for sentence in values if 40 <= len(sentence) <= 700)[:5]


def extract_brands(text: str, products: list[str]) -> list[str]:
    values = []
    for match in re.finditer(r"([A-Z][A-Za-z0-9+&'/, -]{2,100})\s*\(owned \d+% by the Company\)\s+branded", text):
        values.extend(split_named_list(match.group(1)))
    generic = {"advertising", "subscription fees", "affiliate fees", "linear networks", "direct-to-consumer", "theatrical distribution", "music distribution", "home entertainment distribution", "content sales/licensing", "other revenue"}
    values.extend(
        product
        for product in products
        if product.lower() not in generic and re.fullmatch(r"[A-Z][A-Za-z0-9+.-]{1,30}", product)
    )
    return unique_values(values)[:15]


def business_model_summary(text: str, company_name: str, segments: list[str], revenues: list[str]) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text[:5000])
    description = next((sentence for sentence in sentences if company_name.lower().split()[0] in sentence.lower() and 40 < len(sentence) < 500), "")
    parts = [description.strip()]
    if segments:
        parts.append(f"Reported segments: {', '.join(segments)}.")
    if revenues:
        parts.append(f"Reported revenue mechanisms include {', '.join(revenues)}.")
    return " ".join(part for part in parts if part)[:1500]


def extract_heading_labels(text: str, *, limit: int) -> list[str]:
    values = [clean_label(match.group(1)) for match in re.finditer(r"\b([A-Z][A-Z &/-]{3,40})\s+The\s+", text[:18000])]
    return unique_values(value.title() for value in values if is_useful_label(value))[:limit]


def split_named_list(value: str) -> list[str]:
    normalized = re.sub(r"\([^)]*\)", "", value)
    return [clean_label(item) for item in re.split(r",|;|\band\b", normalized) if is_useful_label(clean_label(item))]


def clean_label(value: str) -> str:
    return " ".join(value.strip(" :-–—.,\n\t").split())


def is_useful_label(value: str) -> bool:
    blocked = {"the company", "other", "revenues", "expenses", "domestic", "international", "business", "overview"}
    return 2 <= len(value) <= 90 and value.lower() not in blocked and not value.isdigit()


def unique_values(values) -> list[str]:
    output = []
    seen = set()
    for value in values:
        cleaned = clean_label(str(value))
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            output.append(cleaned)
    return output
