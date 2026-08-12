from __future__ import annotations

import re

from apps.ingestion.models import SourceGapResolutionCandidate


PRIMARY_SOURCE_APIS = {"OFFICIAL_WEBSITE", "SEC", "SEC_EDGAR", "SEC_EDGAR_EXHIBIT"}
PRICE_PATTERN = re.compile(
    r"(?:\$\s?\d|\b(?:USD|EUR|GBP|CAD|AUD)\s?\d|\b\d+(?:\.\d{1,2})?\s?(?:USD|EUR|GBP|CAD|AUD)\b)",
    re.IGNORECASE,
)
PRODUCT_CONTEXT_PATTERN = re.compile(
    r"\b(?:product|fuel|lubricant|chemical|specialty|plan|package|grade|service)\b",
    re.IGNORECASE,
)
GEOGRAPHY_CONTEXT_PATTERN = re.compile(
    r"\b(?:project|field|facility|country|region|offshore|basin|terminal|refinery|plant|market)\b",
    re.IGNORECASE,
)


def is_promotable_energy_candidate(candidate: SourceGapResolutionCandidate) -> bool:
    """Require explicit, first-party evidence before promoting Energy-sector gaps."""
    if candidate.company.industry != "Energy":
        return True
    if candidate.dashboard not in {"product_pricing_history", "geographic_expansion", "acquisition_lifecycle"}:
        return True
    if candidate.source_document.source_api not in PRIMARY_SOURCE_APIS:
        return False

    evidence = candidate.evidence_text or ""
    if candidate.dashboard == "product_pricing_history":
        return bool(PRICE_PATTERN.search(evidence) and PRODUCT_CONTEXT_PATTERN.search(evidence))
    if candidate.dashboard == "geographic_expansion":
        return bool(GEOGRAPHY_CONTEXT_PATTERN.search(evidence))
    return bool(re.search(r"\b(?:acquired|acquisition|merger|purchase agreement)\b", evidence, re.IGNORECASE))
