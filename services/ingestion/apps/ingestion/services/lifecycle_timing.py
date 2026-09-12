"""Evidence-first lifecycle timing helpers for founder comparisons."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
import re
from typing import Any, Iterable

MONTH_NAMES = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
EXACT_DAY_PATTERN = re.compile(
    rf"\b(?:on|effective(?:\s+as\s+of)?|beginning\s+on|commencing\s+on)\s+"
    rf"({MONTH_NAMES})\s+(\d{{1,2}}),\s*(\d{{4}})\b",
    re.IGNORECASE,
)
ACTION_THEN_DAY_PATTERN = re.compile(
    rf"\b(?:acquired|acquire|completed|closed|launched|introduced|entered\s+into|"
    rf"commenced|began|restructured|invested|announced|formed|merged)\b[^.{{}}]{{0,180}}?"
    rf"(?:on\s+)?({MONTH_NAMES})\s+(\d{{1,2}}),\s*(\d{{4}})\b",
    re.IGNORECASE,
)
ACTION_MARKERS = (
    "acquired", "acquire", "completed", "closed", "launched", "introduced",
    "entered into", "commenced", "began", "restructured", "invested", "announced",
    "formed", "merged",
)


def exact_action_date_from_evidence(text: str) -> tuple[date, str] | None:
    """Return an explicitly stated day from an already-extracted event sentence.

    Filing/publication dates are intentionally never inferred as action dates.
    """
    if not text:
        return None
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        match = EXACT_DAY_PATTERN.search(sentence) or ACTION_THEN_DAY_PATTERN.search(sentence)
        if not match or not _has_action_marker(sentence):
            continue
        try:
            action_date = date.fromisoformat(
                f"{match.group(3)}-{_month_number(match.group(1)):02d}-{int(match.group(2)):02d}"
            )
        except ValueError:
            continue
        return action_date, sentence.strip()
    return None


def evidenced_relative_date(expression: str, *, document_date: date | None) -> tuple[date | None, date | None, str]:
    """Resolve only simple relative expressions against an evidenced document date.

    The original phrase is always retained.  Without a document date, no date is
    invented; callers must leave the candidate time UNKNOWN.
    """
    phrase = (expression or "").strip()
    if not document_date or not phrase:
        return None, None, phrase
    normalized = phrase.lower()
    if normalized in {"today", "on that day"}:
        return document_date, document_date, phrase
    return None, None, phrase


def lifecycle_context_from_financial_facts(
    *,
    company: Any,
    action_date: date,
    financial_facts: Iterable[Any],
) -> dict[str, Any] | None:
    """Choose a primary-source scale fact known no later than the action date.

    A fact must describe a period within roughly one fiscal year of the action; this
    prevents current revenue being presented as historical lifecycle context.
    """
    preferred = (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "Assets",
    )
    candidates = [fact for fact in financial_facts if _is_contemporaneous(fact, action_date)]
    if not candidates:
        return None
    candidates.sort(
        key=lambda fact: (
            preferred.index(getattr(fact, "concept", ""))
            if getattr(fact, "concept", "") in preferred else len(preferred),
            -_fact_as_of_date(fact).toordinal(),
        )
    )
    fact = candidates[0]
    as_of_date = _fact_as_of_date(fact)
    return {
        "as_of_date": as_of_date.isoformat(),
        "source_url": sec_filing_url(company, getattr(fact, "accession_number", "")),
        "metrics": [{
            "label": getattr(fact, "label", "") or getattr(fact, "concept", "Financial metric"),
            "value": format_financial_value(getattr(fact, "value", None), getattr(fact, "unit", "")),
            "concept": getattr(fact, "concept", ""),
            "accession_number": getattr(fact, "accession_number", ""),
        }],
    }


def sec_filing_url(company: Any, accession_number: str) -> str:
    cik = str(getattr(company, "sec_cik", "") or "").lstrip("0")
    accession = str(accession_number or "").replace("-", "")
    if cik and accession:
        return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/"
    return ""


def format_financial_value(value: Any, unit: str) -> str:
    try:
        number = Decimal(str(value))
    except Exception:
        return str(value or "")
    prefix = "$" if unit.upper() == "USD" else ""
    magnitude = ""
    divisor = Decimal("1")
    if abs(number) >= Decimal("1000000000"):
        divisor, magnitude = Decimal("1000000000"), "B"
    elif abs(number) >= Decimal("1000000"):
        divisor, magnitude = Decimal("1000000"), "M"
    elif abs(number) >= Decimal("1000"):
        divisor, magnitude = Decimal("1000"), "K"
    rendered = (number / divisor).quantize(Decimal("0.1")) if divisor != 1 else number
    return f"{prefix}{rendered}{magnitude}" if prefix or magnitude else str(rendered)


def _is_contemporaneous(fact: Any, action_date: date) -> bool:
    filed = getattr(fact, "filed", None)
    if not filed or filed > action_date:
        return False
    as_of_date = _fact_as_of_date(fact)
    return 0 <= (action_date - as_of_date).days <= 400


def _fact_as_of_date(fact: Any) -> date:
    raw = getattr(fact, "raw", None) or {}
    for key in ("end", "start"):
        value = raw.get(key) if isinstance(raw, dict) else None
        if value:
            try:
                return date.fromisoformat(str(value))
            except ValueError:
                pass
    return getattr(fact, "filed")


def _has_action_marker(sentence: str) -> bool:
    normalized = sentence.lower()
    return any(marker in normalized for marker in ACTION_MARKERS)


def _month_number(name: str) -> int:
    return ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"].index(name.lower()) + 1
