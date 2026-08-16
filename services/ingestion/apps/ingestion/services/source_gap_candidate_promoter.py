from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import re

from django.utils import timezone

from apps.companies.models import (
    CompanyProfileStatus,
    CustomerSupplierDependency,
    CustomerSupplierDependencySnapshot,
    DependencyContractTerm,
    DependencyContractTermType,
    DependencyDisclosureConfidence,
    DependencyMaterialityBand,
    DependencyType,
    OwnershipHolderType,
    OwnershipInsiderSnapshot,
    OwnershipPosition,
    OwnershipPositionType,
    PromiseReviewStatus,
)
from apps.ingestion.models import ArticleExtraction, SourceGapResolutionCandidate, SourceGapStatus
from apps.ingestion.services.energy_source_quality import is_promotable_energy_candidate


@dataclass(frozen=True)
class PromotionResult:
    candidates_checked: int
    dashboard_rows_created: int
    dashboard_rows_updated: int
    candidates_promoted: int
    candidates_skipped: int


def promote_source_gap_candidates(*, limit: int = 100, dashboard: str = "", gap_type: str = "") -> PromotionResult:
    candidates = (
        SourceGapResolutionCandidate.objects.filter(
            extraction_status="EXTRACTED",
            review_status="NEEDS_REVIEW",
            company__isnull=False,
        )
        .select_related("company", "source_document", "source_gap")
        .order_by("company_id", "dashboard", "gap_type", "-confidence_score")
    )
    if dashboard:
        candidates = candidates.filter(dashboard=dashboard)
    if gap_type:
        candidates = candidates.filter(gap_type=gap_type)

    checked = created = updated = promoted = skipped = 0
    for candidate in candidates[:limit]:
        checked += 1
        counters = promote_candidate(candidate)
        if counters["promoted"]:
            created += counters["created"]
            updated += counters["updated"]
            promoted += 1
            mark_candidate_promoted(candidate, counters)
        else:
            skipped += 1
            candidate.metadata = {
                **safe_metadata(candidate),
                "promotion_status": "SKIPPED",
                "promotion_reason": counters["reason"],
            }
            candidate.save(update_fields=["metadata", "updated_at"])
    return PromotionResult(
        candidates_checked=checked,
        dashboard_rows_created=created,
        dashboard_rows_updated=updated,
        candidates_promoted=promoted,
        candidates_skipped=skipped,
    )


def promote_candidate(candidate: SourceGapResolutionCandidate) -> dict[str, object]:
    if not is_promotable_energy_candidate(candidate):
        return {
            "promoted": False,
            "created": 0,
            "updated": 0,
            "reason": "Energy candidates require explicit first-party product, price, or market evidence",
        }
    if candidate.dashboard == "ownership_insider_activity" and candidate.gap_type in {"ownership_percentages", "voting_control", "institutional_positions"}:
        return promote_ownership_candidate(candidate)
    if candidate.dashboard == "customer_supplier_dependency" and candidate.gap_type == "concentration_percentages":
        return promote_dependency_concentration_candidate(candidate)
    if candidate.dashboard == "customer_supplier_dependency" and candidate.gap_type == "dependency_contract_terms":
        return promote_dependency_contract_candidate(candidate)
    return {"promoted": False, "created": 0, "updated": 0, "reason": "unsupported gap type for deterministic promotion"}


def promote_ownership_candidate(candidate: SourceGapResolutionCandidate) -> dict[str, object]:
    rows = parse_ownership_rows(source_text(candidate), gap_type=candidate.gap_type)
    if not rows:
        return {"promoted": False, "created": 0, "updated": 0, "reason": "no explicit holder percentage found"}
    snapshot = ownership_snapshot(candidate)
    created = updated = 0
    for row in rows[:8]:
        position, was_created = OwnershipPosition.objects.update_or_create(
            snapshot=snapshot,
            holder_name=row["holder_name"],
            holder_type=row["holder_type"],
            position_type=row["position_type"],
            defaults={
                "economic_ownership_pct": row["economic_ownership_pct"],
                "voting_power_pct": row["voting_power_pct"],
                "shares_owned": row["shares_owned"],
                "share_class": row["share_class"],
                "filing_date": source_date(candidate),
                "report_period": row["report_period"],
                "disclosure_form": disclosure_form(candidate),
                "evidence_text": candidate.evidence_text,
                "source_document": candidate.source_document,
                "confidence_score": "0.860",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    refresh_ownership_summary(snapshot)
    return {"promoted": True, "created": created, "updated": updated, "reason": ""}


def promote_dependency_concentration_candidate(candidate: SourceGapResolutionCandidate) -> dict[str, object]:
    rows = parse_dependency_concentrations(source_text(candidate))
    if not rows:
        return {"promoted": False, "created": 0, "updated": 0, "reason": "no explicit customer concentration percentage found"}
    snapshot = dependency_snapshot(candidate)
    created = updated = 0
    for row in rows[:6]:
        dependency, was_created = CustomerSupplierDependency.objects.update_or_create(
            snapshot=snapshot,
            dependency_type=DependencyType.CUSTOMER,
            counterparty_name=row["counterparty_name"],
            product_scope=row["product_scope"],
            defaults={
                "counterparty_company": None,
                "is_named_counterparty": row["is_named_counterparty"],
                "materiality_band": DependencyMaterialityBand.CONCENTRATION_DISCLOSED,
                "disclosure_confidence": DependencyDisclosureConfidence.NAMED if row["is_named_counterparty"] else DependencyDisclosureConfidence.UNNAMED,
                "concentration_percent": row["concentration_percent"],
                "geography": "",
                "relationship_summary": row["relationship_summary"],
                "risk_summary": "Customer concentration is source-disclosed; renewal and contract terms are not inferred from this excerpt.",
                "evidence_text": candidate.evidence_text,
                "source_document": candidate.source_document,
                "confidence_score": "0.850",
            },
        )
        DependencyContractTerm.objects.update_or_create(
            dependency=dependency,
            term_type=DependencyContractTermType.CONCENTRATION,
            description=row["relationship_summary"],
            defaults={
                "effective_date": source_date(candidate),
                "evidence_text": candidate.evidence_text,
                "source_document": candidate.source_document,
                "confidence_score": "0.850",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    refresh_dependency_summary(snapshot)
    return {"promoted": True, "created": created, "updated": updated, "reason": ""}


def promote_dependency_contract_candidate(candidate: SourceGapResolutionCandidate) -> dict[str, object]:
    rows = parse_dependency_contract_terms(source_text(candidate))
    if not rows:
        return {"promoted": False, "created": 0, "updated": 0, "reason": "no named counterparty with an explicit contract term found"}
    snapshot = dependency_snapshot(candidate)
    created = updated = 0
    for row in rows[:4]:
        dependency, was_created = CustomerSupplierDependency.objects.update_or_create(
            snapshot=snapshot,
            dependency_type=row["dependency_type"],
            counterparty_name=row["counterparty_name"],
            product_scope=row["product_scope"],
            defaults={
                "counterparty_company": None,
                "is_named_counterparty": True,
                "materiality_band": DependencyMaterialityBand.DISCLOSED_MATERIAL,
                "disclosure_confidence": DependencyDisclosureConfidence.NAMED,
                "concentration_percent": None,
                "geography": "",
                "relationship_summary": row["relationship_summary"],
                "risk_summary": "Source-disclosed contract terms are shown without estimating commercial exposure.",
                "evidence_text": row["evidence_text"],
                "source_document": candidate.source_document,
                "confidence_score": "0.880",
            },
        )
        for term in row["terms"]:
            DependencyContractTerm.objects.update_or_create(
                dependency=dependency,
                term_type=term,
                description=row["description"],
                defaults={
                    "effective_date": source_date(candidate),
                    "expiration_date": None,
                    "evidence_text": row["evidence_text"],
                    "source_document": candidate.source_document,
                    "confidence_score": "0.880",
                    "review_status": PromiseReviewStatus.REVIEWED,
                },
            )
        created += 1 if was_created else 0
        updated += 0 if was_created else 1
    refresh_dependency_summary(snapshot)
    return {"promoted": True, "created": created, "updated": updated, "reason": ""}


OWNERSHIP_PATTERNS = (
    re.compile(
        r"(?P<holder>[A-Z][A-Za-z0-9&.,'() -]{2,90}?)\s+(?:beneficially\s+)?(?:owned|owns|held|holds)\s+"
        r"(?:(?P<shares>[0-9][0-9,]*(?:\.\d+)?)\s+shares?.{0,80}?)?"
        r"(?P<pct>\d{1,2}(?:\.\d{1,4})?)\s*%",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<holder>[A-Z][A-Za-z0-9&.,'() -]{2,90}?)\s+.{0,40}?(?:beneficial ownership|voting power).{0,60}?"
        r"(?P<pct>\d{1,2}(?:\.\d{1,4})?)\s*%",
        re.IGNORECASE,
    ),
)


def parse_ownership_rows(text: str, *, gap_type: str) -> list[dict[str, object]]:
    return parse_schedule_ownership_rows(text, gap_type=gap_type)


def parse_schedule_ownership_rows(text: str, *, gap_type: str) -> list[dict[str, object]]:
    normalized = normalize(text)
    holder = schedule_holder_name(normalized)
    pct_match = re.search(r"percent of class represented by amount in row\s*\(?9\)?\s+(?P<pct>\d{1,2}(?:\.\d{1,4})?)\s*%", normalized, re.IGNORECASE)
    shares_match = re.search(r"aggregate amount beneficially owned by each reporting person\s+(?P<shares>[0-9][0-9,]*(?:\.\d+)?)", normalized, re.IGNORECASE)
    if not holder or not pct_match:
        return []
    pct = decimal_percent(pct_match.group("pct"))
    if pct is None:
        return []
    return [{
        "holder_name": holder[:255],
        "holder_type": holder_type(holder),
        "position_type": OwnershipPositionType.VOTING_CONTROL if gap_type == "voting_control" else (
            OwnershipPositionType.INSTITUTIONAL_POSITION if holder_type(holder) == OwnershipHolderType.INSTITUTIONAL else OwnershipPositionType.BENEFICIAL_OWNERSHIP
        ),
        "economic_ownership_pct": None if gap_type == "voting_control" else pct,
        "voting_power_pct": pct if gap_type == "voting_control" else None,
        "shares_owned": decimal_number(shares_match.group("shares")) if shares_match else None,
        "share_class": share_class_near(normalized, pct_match.start(), pct_match.end()),
        "report_period": "",
    }]


def schedule_holder_name(text: str) -> str:
    patterns = (
        r"Item\s+2\.\s*\(a\)\s*Name of Person Filing:\s*(?P<name>.*?)(?:\s+\(b\)|\s+Address of Principal|\s+Item\s+2\.\s*\(b\))",
        r"Item\s+2\(a\)\s*[-–]\s*Name of Person Filing:\s*(?P<name>.*?)(?:\s+Item\s+2\(b\)|\s+Address of Principal)",
        r"\(1\)\s*Names? of reporting persons?\.?\s*(?P<name>.*?)(?:\s+\(2\)|\s+Check the appropriate box)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return clean_name(re.sub(r"\s+-\s+\d[\d-]+$", "", match.group("name")))
    return ""


CONCENTRATION_PATTERNS = (
    re.compile(
        r"(?P<name>[A-Z][A-Za-z0-9&.,'() -]{1,90}|one customer|a customer|single customer|major customer)\s+"
        r"(?:accounted for|represented|comprised)\s+(?P<pct>\d{1,2}(?:\.\d{1,4})?)\s*%\s+of\s+"
        r"(?P<scope>net sales|sales|revenue|revenues|net revenue)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<pct>\d{1,2}(?:\.\d{1,4})?)\s*%\s+of\s+(?P<scope>net sales|sales|revenue|revenues|net revenue)\s+"
        r"(?:was|were)?\s*(?:attributable to|from)\s+(?P<name>[A-Z][A-Za-z0-9&.,'() -]{1,90}|one customer|a customer|single customer|major customer)",
        re.IGNORECASE,
    ),
)


def parse_dependency_concentrations(text: str) -> list[dict[str, object]]:
    rows = []
    seen = set()
    normalized = normalize(text)
    if re.search(r"no (?:single |major )?customer.{0,50}(?:10|ten)\s*%\s+or\s+more", normalized, re.IGNORECASE):
        return []
    for pattern in CONCENTRATION_PATTERNS:
        for match in pattern.finditer(normalized):
            pct = decimal_percent(match.group("pct"))
            if pct is None:
                continue
            name = clean_name(match.group("name"))
            is_named = name.lower() not in {"one customer", "a customer", "single customer", "major customer"}
            counterparty = name if is_named else "Unnamed customer"
            scope = clean_name(match.group("scope")).lower()
            key = (counterparty.lower(), scope, str(pct))
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "counterparty_name": counterparty[:255],
                "is_named_counterparty": is_named,
                "concentration_percent": pct,
                "product_scope": scope[:255],
                "relationship_summary": f"{counterparty} accounted for {pct}% of {scope}.",
            })
    return rows


EXCLUSIVE_DISTRIBUTION_PATTERN = re.compile(
    r"(?:pursuant to|under)\s+(?:an|the)\s+(?:agreement|contract)\b.{0,260}?"
    r"\b(?:the\s+company\s+)?is\s+the\s+exclusive\s+(?P<relationship>distributor|licensee)\s+of\s+"
    r"(?P<scope>.{1,180}?)\s+for\s+(?P<term>.{1,120}?)\s+and\s+(?:pays?|payable)\b.{0,160}?"
    r"\bto\s+(?P<counterparty>[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,4})(?=\s+(?:based|under|pursuant)\b|[,.])",
    re.IGNORECASE,
)
CONTRACT_WITH_COUNTERPARTY_PATTERN = re.compile(
    r"\b(?:agreement|contract)\b.{0,100}?\bwith\s+(?P<counterparty>[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*){0,4})(?=\s+(?:that|which|provides|expires|terminates|is|was|will)\b|[,.])",
    re.IGNORECASE,
)


def parse_dependency_contract_terms(text: str) -> list[dict[str, object]]:
    """Return only named, explicit commercial contract terms from source text."""

    normalized = normalize(text)
    rows = []
    for match in EXCLUSIVE_DISTRIBUTION_PATTERN.finditer(normalized):
        terms = contract_term_types(match.group(0))
        counterparty = clean_counterparty(match.group("counterparty"))
        if counterparty and terms:
            scope = clean_name(match.group("scope"))
            rows.append(contract_row(
                counterparty=counterparty,
                dependency_type=DependencyType.DISTRIBUTOR,
                scope=scope,
                description=clean_name(match.group(0)),
                terms=terms,
            ))
    for match in CONTRACT_WITH_COUNTERPARTY_PATTERN.finditer(normalized):
        context = normalized[max(0, match.start() - 120): match.end() + 420]
        terms = contract_term_types(context)
        counterparty = clean_counterparty(match.group("counterparty"))
        if counterparty and terms:
            rows.append(contract_row(
                counterparty=counterparty,
                dependency_type=DependencyType.CONTRACT,
                scope="Source-disclosed contract",
                description=clean_name(context),
                terms=terms,
            ))
    return unique_contract_rows(rows)


def contract_term_types(text: str) -> list[str]:
    terms = []
    normalized = normalize(text)
    if re.search(r"\bexclusive(?:ly|\s+(?:distributor|licensee|right))\b", normalized, re.IGNORECASE):
        terms.append(DependencyContractTermType.EXCLUSIVITY)
    if re.search(r"\brenew(?:al|able|ed)?\b", normalized, re.IGNORECASE):
        terms.append(DependencyContractTermType.RENEWAL)
    if re.search(r"\bexpires?|expiration\b", normalized, re.IGNORECASE):
        terms.append(DependencyContractTermType.EXPIRATION)
    if re.search(r"\bminimum\s+(?:purchase\s+)?commitment\b", normalized, re.IGNORECASE):
        terms.append(DependencyContractTermType.MINIMUM_COMMITMENT)
    if re.search(r"\bterminat(?:e|ed|ion)\b", normalized, re.IGNORECASE):
        terms.append(DependencyContractTermType.TERMINATION)
    return terms


def contract_row(*, counterparty: str, dependency_type: str, scope: str, description: str, terms: list[str]) -> dict[str, object]:
    return {
        "counterparty_name": counterparty[:255],
        "dependency_type": dependency_type,
        "product_scope": scope[:255],
        "relationship_summary": f"{counterparty} is named in a source-disclosed commercial agreement.",
        "description": description[:2000],
        "evidence_text": description[:4000],
        "terms": terms,
    }


def clean_counterparty(value: str) -> str:
    candidate = clean_name(value)
    if candidate.lower() in {"the company", "company", "we", "our company"}:
        return ""
    return candidate


def unique_contract_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    unique = []
    seen = set()
    for row in rows:
        key = (row["counterparty_name"].lower(), row["dependency_type"], row["product_scope"].lower(), tuple(row["terms"]))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique


def ownership_snapshot(candidate: SourceGapResolutionCandidate) -> OwnershipInsiderSnapshot:
    latest = (
        OwnershipInsiderSnapshot.objects.filter(company=candidate.company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if latest:
        latest.source_document = latest.source_document or candidate.source_document
        latest.methodology = append_methodology(
            latest.methodology,
            "Deterministic source-gap promotion adds explicit Schedule 13D/13G ownership percentages to the current dashboard snapshot.",
        )
        latest.save(update_fields=["source_document", "methodology", "updated_at"])
        return latest
    snapshot, _created = OwnershipInsiderSnapshot.objects.update_or_create(
        company=candidate.company,
        effective_date=source_date(candidate),
        defaults={
            "source_document": candidate.source_document,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": f"Source-backed ownership disclosures for {candidate.company.name}.",
            "methodology": "Automatically promoted only from extracted source-gap candidates with explicit holder percentages in official source text.",
            "confidence_score": "0.860",
        },
    )
    return snapshot


def dependency_snapshot(candidate: SourceGapResolutionCandidate) -> CustomerSupplierDependencySnapshot:
    latest = (
        CustomerSupplierDependencySnapshot.objects.filter(company=candidate.company, status__in=[CompanyProfileStatus.PUBLISHED, CompanyProfileStatus.REVIEWED])
        .order_by("-effective_date", "-updated_at")
        .first()
    )
    if latest:
        latest.source_document = latest.source_document or candidate.source_document
        latest.methodology = append_methodology(
            latest.methodology,
            "Deterministic source-gap promotion adds explicit customer concentration percentages to the current dashboard snapshot.",
        )
        latest.save(update_fields=["source_document", "methodology", "updated_at"])
        return latest
    snapshot, _created = CustomerSupplierDependencySnapshot.objects.update_or_create(
        company=candidate.company,
        effective_date=source_date(candidate),
        defaults={
            "source_document": candidate.source_document,
            "status": CompanyProfileStatus.REVIEWED,
            "summary": f"Source-backed dependency disclosures for {candidate.company.name}.",
            "methodology": "Automatically promoted only from extracted source-gap candidates with explicit customer concentration percentages in official source text.",
            "confidence_score": "0.850",
        },
    )
    return snapshot


def mark_candidate_promoted(candidate: SourceGapResolutionCandidate, counters: dict[str, object]) -> None:
    candidate.review_status = "AUTO_PROMOTED"
    candidate.metadata = {
        **safe_metadata(candidate),
        "promotion_status": "AUTO_PROMOTED",
        "dashboard_rows_created": counters["created"],
        "dashboard_rows_updated": counters["updated"],
    }
    candidate.save(update_fields=["review_status", "metadata", "updated_at"])
    if candidate.source_gap_id:
        candidate.source_gap.status = SourceGapStatus.RESOLVED
        candidate.source_gap.metadata = {
            **(candidate.source_gap.metadata if isinstance(candidate.source_gap.metadata, dict) else {}),
            "resolved_by_candidate_id": candidate.id,
            "resolved_by_source_document_id": candidate.source_document_id,
        }
        candidate.source_gap.save(update_fields=["status", "metadata", "updated_at"])


def refresh_ownership_summary(snapshot: OwnershipInsiderSnapshot) -> None:
    pct_count = snapshot.positions.exclude(economic_ownership_pct__isnull=True).count()
    vote_count = snapshot.positions.exclude(voting_power_pct__isnull=True).count()
    snapshot.summary = f"{snapshot.company.name} has {pct_count} source-backed ownership percentage rows and {vote_count} voting-control rows."
    snapshot.save(update_fields=["summary", "updated_at"])


def refresh_dependency_summary(snapshot: CustomerSupplierDependencySnapshot) -> None:
    count = snapshot.dependencies.exclude(concentration_percent__isnull=True).count()
    snapshot.summary = f"{snapshot.company.name} has {count} source-backed customer concentration disclosure rows."
    snapshot.save(update_fields=["summary", "updated_at"])


def append_methodology(current: str, sentence: str) -> str:
    if sentence in (current or ""):
        return current or sentence
    return ((current or "").strip() + " " + sentence).strip()


def source_date(candidate: SourceGapResolutionCandidate) -> date:
    if candidate.source_document and candidate.source_document.published_date:
        return candidate.source_document.published_date.date()
    return timezone.now().date()


def source_text(candidate: SourceGapResolutionCandidate) -> str:
    extraction_id = safe_metadata(candidate).get("article_extraction_id")
    extraction = None
    if extraction_id:
        extraction = ArticleExtraction.objects.filter(id=extraction_id, extraction_status="SUCCEEDED").first()
    if extraction is None:
        extraction = ArticleExtraction.objects.filter(source_document=candidate.source_document, extraction_status="SUCCEEDED").first()
    if extraction and extraction.clean_text:
        return extraction.clean_text
    return candidate.evidence_text


def disclosure_form(candidate: SourceGapResolutionCandidate) -> str:
    title = f"{candidate.source_document.title if candidate.source_document else ''} {candidate.candidate_type}"
    if "DEF 14A" in title.upper():
        return "DEF 14A"
    if "13G" in title.upper():
        return "SC 13G"
    if "13D" in title.upper():
        return "SC 13D"
    return candidate.source_document.source_api if candidate.source_document else "Source document"


def holder_type(holder: str) -> str:
    lowered = holder.lower()
    if any(term in lowered for term in ("blackrock", "vanguard", "state street", "capital group", "fmr", "fidelity")):
        return OwnershipHolderType.INSTITUTIONAL
    if any(term in lowered for term in ("trust", "llc", "inc.", "corp", "fund", "group", "partners")):
        return OwnershipHolderType.STRATEGIC
    return OwnershipHolderType.EXECUTIVE


def voting_percent_near(text: str, start: int, end: int) -> Decimal | None:
    window = normalize(text)[max(0, start - 120): end + 160]
    match = re.search(r"voting (?:power|control).{0,60}?(\d{1,2}(?:\.\d{1,4})?)\s*%", window, re.IGNORECASE)
    return decimal_percent(match.group(1)) if match else None


def share_class_near(text: str, start: int, end: int) -> str:
    window = normalize(text)[max(0, start - 120): end + 160]
    match = re.search(r"(Class\s+[A-Z](?:\s+common)?\s+stock|common stock|ordinary shares)", window, re.IGNORECASE)
    return clean_name(match.group(1))[:128] if match else ""


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def clean_name(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value or "").strip(" .;:-")
    cleaned = re.sub(r"^(and|or|the)\s+", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def decimal_percent(value: str | None) -> Decimal | None:
    parsed = decimal_number(value)
    if parsed is None or parsed < 0 or parsed > 100:
        return None
    return parsed


def decimal_number(value: str | None) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def safe_metadata(candidate: SourceGapResolutionCandidate) -> dict:
    return candidate.metadata if isinstance(candidate.metadata, dict) else {}
