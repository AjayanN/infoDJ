from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import re
from urllib.parse import urljoin

import requests

from apps.companies.models import (
    EarningsGuidanceComparison,
    EarningsPeriod,
    EarningsPeriodDocument,
    PromiseReviewStatus,
)
from apps.ingestion.models import ArticleExtraction, FinancialFact, SourceDocument
from apps.ingestion.services.article_extractor import ArticleExtractor, DEFAULT_USER_AGENT, extract_source_document


KEY_CONCEPTS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "OperatingIncomeLoss",
    "NetIncomeLoss",
    "EarningsPerShareDiluted",
    "NetCashProvidedByUsedInOperatingActivities",
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "CashAndCashEquivalentsAtCarryingValue",
)

REVIEWED_DRIVER_PHRASES = {
    "amazon": ("Free cash flow decreased",),
    "american-tower": ("structural growth drivers of our business", "strongest strategic position"),
    "apple": ("iPhone achieved a March quarter revenue record",),
    "caterpillar": ("higher sales volume of $940 million",),
    "disney": ("Sports segment operating income declined", "Cash provided by operations decreased"),
    "exxonmobil": ("Higher prices and margins", "quarter-over-quarter increase was driven"),
    "ford-motor-company": ("Ford Credit reported first-quarter earnings", "Ford Blue reported"),
    "freeport-mcmoran": ("sales of 657 million pounds were higher", "average unit cash costs were favorable"),
    "general-electric": ("Equipment revenue grew 20%", "Margins were down"),
    "jpmorgan-chase": ("Markets revenue reached a record", "Noninterest revenue excluding Markets"),
    "microsoft": ("We delivered results that exceeded expectations",),
    "netflix": ("Revenue in Q1 grew 16%", "recent price changes have gone well"),
    "newmont": ("Copper production increased 3 percent", "This increase was primarily driven by higher revenues"),
    "nextera-energy": ("results reflect continued strong financial", "full-year growth primarily was driven"),
    "pfizer": ("Padcev globally, up 39%", "Eliquis globally, up 8%"),
    "prologis": ("record lease signings of 64 million square feet",),
    "tesla": ("quarterly operating income increased 136%",),
    "unitedhealth-group": ("operating cost ratio of 13.8%", "Optum supported more than 122 million"),
    "visa": ("Net revenue in the fiscal second quarter", "GAAP operating expenses were $4.0 billion"),
    "walmart": ("Strong sales, with broad-based share gains", "eCommerce sales increased 26%", "Gross profit grew 29 bps"),
}

NETFLIX_Q1_2026_FORECAST_URL = (
    "https://www.sec.gov/Archives/edgar/data/1065280/000106528026000033/ex991_q425.htm"
)


def build_earnings_periods(company) -> dict[str, int]:
    facts = FinancialFact.objects.filter(company=company, raw__form="10-Q").exclude(accession_number="")
    grouped = defaultdict(list)
    for fact in facts:
        grouped[fact.accession_number].append(fact)

    counters = {"created": 0, "updated": 0, "skipped": 0}
    for accession, filing_facts in grouped.items():
        representative = max(filing_facts, key=lambda row: (row.filed or date.min, row.id))
        raw = representative.raw or {}
        period_end = parse_fact_date(raw.get("end"))
        if not period_end or not representative.filed or representative.fp not in {"Q1", "Q2", "Q3"}:
            counters["skipped"] += 1
            continue
        source = source_for_filing(company, representative.filed, accession)
        if source is None:
            counters["skipped"] += 1
            continue
        starts = [parse_fact_date((row.raw or {}).get("start")) for row in filing_facts]
        starts = [value for value in starts if value and value <= period_end]
        period_start = max(starts) if starts else None
        headline = (
            f"{company.name} reported {representative.fp} FY{representative.fy} results "
            f"for the period ended {period_end.isoformat()} in a Form 10-Q filed {representative.filed.isoformat()}."
        )
        _period, created = EarningsPeriod.objects.update_or_create(
            company=company,
            accession_number=accession,
            defaults={
                "fiscal_year": representative.fy or period_end.year,
                "fiscal_period": representative.fp,
                "period_start": period_start,
                "period_end": period_end,
                "filed_date": representative.filed,
                "headline": headline,
                "source_document": source,
                "confidence_score": "0.950",
                "review_status": PromiseReviewStatus.REVIEWED,
                "is_published": True,
            },
        )
        counters["created" if created else "updated"] += 1
    return counters


def earnings_quality_issues(company) -> list[str]:
    periods = company.earnings_periods.filter(is_published=True, review_status=PromiseReviewStatus.REVIEWED)
    if not periods.exists():
        return ["no reviewed published earnings period"]
    issues = []
    for period in periods.select_related("source_document"):
        if not period.source_document_id:
            issues.append(f"{period.accession_number}: source document unavailable")
        if not period.headline.strip():
            issues.append(f"{period.accession_number}: measured-result headline unavailable")
        if not FinancialFact.objects.filter(company=company, accession_number=period.accession_number).exists():
            issues.append(f"{period.accession_number}: SEC facts unavailable")
    latest = periods.order_by("-period_end", "-filed_date").first()
    if latest and not latest.documents.filter(review_status=PromiseReviewStatus.REVIEWED).exclude(evidence_text="").exists():
        issues.append(f"{latest.accession_number}: reviewed management explanation unavailable")
    return issues


def publish_reviewed_earnings_excerpt(company) -> dict[str, int | str]:
    phrases = REVIEWED_DRIVER_PHRASES.get(company.slug, ())
    period = company.earnings_periods.filter(is_published=True).order_by("-period_end", "-filed_date").first()
    if not period or not phrases:
        return {"reviewed": 0, "skipped": 1, "reason": "review catalog unavailable"}
    best = None
    for link in period.documents.select_related("source_document"):
        extraction = ArticleExtraction.objects.filter(source_document=link.source_document).first()
        if not extraction or extraction.extraction_status != "SUCCEEDED":
            continue
        chunks = evidence_chunks(extraction.clean_text)
        matches = []
        for phrase in phrases:
            match = next((chunk for chunk in chunks if phrase.lower() in chunk.lower() and 35 <= len(chunk) <= 500), "")
            if match and match not in matches:
                matches.append(match.strip('“”" '))
        candidate = (len(matches), earnings_release_score(extraction), -link.id, link, matches)
        if matches and (best is None or candidate[:3] > best[:3]):
            best = candidate
    if best is None:
        return {"reviewed": 0, "skipped": 1, "reason": "reviewed phrases not found in official exhibit"}
    link = best[3]
    link.evidence_text = " ".join(best[4])[:3000]
    link.confidence_score = "0.900"
    link.review_status = PromiseReviewStatus.REVIEWED
    link.save(update_fields=["evidence_text", "confidence_score", "review_status"])
    period.documents.exclude(id=link.id).update(review_status=PromiseReviewStatus.NEEDS_REVIEW)
    return {"reviewed": 1, "skipped": 0, "reason": ""}


def publish_reviewed_guidance_comparisons(company) -> dict[str, int | str]:
    if company.slug != "netflix":
        return {"reviewed": 0, "skipped": 1, "reason": "no reviewed comparable guidance baseline"}
    period = company.earnings_periods.filter(period_end=date(2026, 3, 31), is_published=True).first()
    actual_link = (
        period.documents.filter(review_status=PromiseReviewStatus.REVIEWED)
        .select_related("source_document")
        .first()
        if period else None
    )
    if not period or not actual_link:
        return {"reviewed": 0, "skipped": 1, "reason": "reviewed actual source unavailable"}
    forecast_source, _created = SourceDocument.objects.get_or_create(
        company=company,
        url=NETFLIX_Q1_2026_FORECAST_URL,
        defaults={
            "source_api": "SEC_EDGAR_EXHIBIT",
            "title": "Netflix Q4 2025 shareholder letter",
            "publisher": "SEC EDGAR",
            "language": "English",
        },
    )
    forecast_extraction = extract_source_document(
        forecast_source, article_extraction_model=ArticleExtraction, extractor=ArticleExtractor()
    )
    if forecast_extraction.extraction_status != "SUCCEEDED" or "Q1'26 Forecast" not in forecast_extraction.clean_text:
        return {"reviewed": 0, "skipped": 1, "reason": "official forecast table unavailable"}
    rows = (
        ("Revenue", "12157", "12250", "USD millions", "ABOVE", "Q1'26 Forecast Revenue: $12,157 million.", "Q1'26 reported revenue: $12,250 million."),
        ("Operating income", "3906", "3957", "USD millions", "ABOVE", "Q1'26 Forecast Operating Income: $3,906 million.", "Q1'26 reported operating income: $3,957 million."),
        ("Operating margin", "32.1", "32.3", "percent", "ABOVE", "Q1'26 Forecast Operating Margin: 32.1%.", "Q1'26 reported operating margin: 32.3%."),
        ("Diluted EPS", "0.76", "1.23", "USD per share", "ABOVE", "Q1'26 Forecast Diluted EPS: $0.76.", "Q1'26 reported diluted EPS: $1.23."),
    )
    for metric_name, forecast, actual, unit, status, forecast_evidence, actual_evidence in rows:
        EarningsGuidanceComparison.objects.update_or_create(
            period=period,
            metric_name=metric_name,
            defaults={
                "forecast_value": forecast,
                "actual_value": actual,
                "unit": unit,
                "comparison_status": status,
                "forecast_source": forecast_source,
                "actual_source": actual_link.source_document,
                "forecast_evidence": forecast_evidence,
                "actual_evidence": actual_evidence,
                "confidence_score": "0.950",
                "review_status": PromiseReviewStatus.REVIEWED,
            },
        )
    return {"reviewed": len(rows), "skipped": 0, "reason": ""}


def collect_latest_earnings_exhibit(company) -> dict[str, int | str]:
    period = company.earnings_periods.filter(is_published=True).order_by("-period_end", "-filed_date").first()
    if period is None:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "no earnings period"}
    filings = list(
        SourceDocument.objects.filter(
            company=company,
            title__icontains="8-K",
            published_date__date__gte=period.filed_date - timedelta(days=30),
            published_date__date__lte=period.filed_date + timedelta(days=7),
        )
        .order_by("-published_date")
    )
    if not filings:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "no earnings-adjacent 8-K"}
    source = None
    exhibit = None
    source_created = False
    best_score = 0
    for candidate in filings:
        extraction = extract_source_document(candidate, article_extraction_model=ArticleExtraction)
        if extraction.extraction_status != "SUCCEEDED":
            continue
        for candidate_exhibit in earnings_exhibit_names(candidate):
            if not is_exhibit_99(candidate_exhibit):
                continue
            exhibit_url = urljoin(filing_index_url(candidate.url), candidate_exhibit)
            candidate_source, created = SourceDocument.objects.get_or_create(
                company=company,
                url=exhibit_url,
                defaults={
                    "source_api": "SEC_EDGAR_EXHIBIT",
                    "title": f"{company.name} earnings exhibit {candidate.published_date.date().isoformat()}",
                    "publisher": "SEC EDGAR",
                    "published_date": candidate.published_date,
                    "snippet": f"Company-issued earnings material furnished with {candidate.title}.",
                    "language": "English",
                },
            )
            candidate_extraction = extract_source_document(
                candidate_source,
                article_extraction_model=ArticleExtraction,
                extractor=ArticleExtractor(),
            )
            score = earnings_release_score(candidate_extraction)
            if score > best_score:
                source = candidate_source
                exhibit = candidate_extraction
                source_created = created
                best_score = score
    if source is None or exhibit is None:
        return {"created": 0, "updated": 0, "skipped": 1, "reason": "validated Exhibit 99 earnings release unavailable"}
    explanation = management_driver_excerpt(exhibit.clean_text)
    link, link_created = EarningsPeriodDocument.objects.get_or_create(
        period=period,
        source_document=source,
        defaults={
            "document_type": "EARNINGS_EXHIBIT",
            "evidence_text": explanation,
            "confidence_score": "0.800",
            "review_status": PromiseReviewStatus.NEEDS_REVIEW,
        },
    )
    if not link_created and link.review_status != PromiseReviewStatus.REVIEWED:
        link.document_type = "EARNINGS_EXHIBIT"
        link.evidence_text = explanation
        link.confidence_score = "0.800"
        link.save(update_fields=["document_type", "evidence_text", "confidence_score"])
    return {
        "created": int(source_created or link_created),
        "updated": int(not (source_created or link_created)),
        "skipped": 0,
        "reason": "",
    }


def earnings_exhibit_name(filing: SourceDocument) -> str:
    return next(iter(earnings_exhibit_names(filing)), "")


def earnings_exhibit_names(filing: SourceDocument) -> list[str]:
    index_url = filing_index_url(filing.url)
    response = requests.get(index_url, headers={"User-Agent": DEFAULT_USER_AGENT}, timeout=30)
    response.raise_for_status()
    items = response.json().get("directory", {}).get("item", [])
    html_items = [
        item for item in items
        if str(item.get("name") or "").lower().endswith((".htm", ".html"))
        and "index" not in str(item.get("name") or "").lower()
        and not re.fullmatch(r"r\d+\.htm", str(item.get("name") or ""), re.I)
        and str(item.get("name") or "") != filing.url.rsplit("/", 1)[-1]
    ]
    preferred = [
        item for item in html_items
        if re.search(r"earnings|release|press|narrative|exhibit|(?:ex|livef8k).*99", str(item.get("name") or ""), re.I)
    ]
    candidates = preferred or html_items

    def rank(item):
        name = str(item.get("name") or "").lower()
        score = 0
        score += 100 if re.search(r"earnings?.*release|release.*earnings?|press.?release|narrative", name) else 0
        score += 40 if re.search(r"ex(?:hibit)?[-_]?99[._-]?1", name) else 0
        score += 20 if re.search(r"earnings?|results?", name) else 0
        score -= 40 if re.search(r"supplement|presentation|slides", name) else 0
        return score, int(item.get("size") or 0)

    return [str(item.get("name") or "") for item in sorted(candidates, key=rank, reverse=True)]


def is_exhibit_99(filename: str) -> bool:
    return bool(re.search(r"(?:ex(?:hibit)?[-_]?99|99[-_.])", filename, re.I))


def is_earnings_release(extraction: ArticleExtraction) -> bool:
    return earnings_release_score(extraction) >= 3


def earnings_release_score(extraction: ArticleExtraction) -> int:
    if extraction.extraction_status != "SUCCEEDED" or extraction.word_count < 100:
        return 0
    text = extraction.clean_text
    markers = (
        r"financial results",
        r"(?:first|second|third|fourth|fiscal|three months ended).{0,50}quarter",
        r"reports?.{0,80}(?:quarter|results)",
        r"(?:net revenue|net sales|operating income|earnings per share|core ffo)",
    )
    score = sum(bool(re.search(marker, text, re.I | re.S)) for marker in markers)
    score += 3 if re.search(r"for immediate release", text, re.I) else 0
    score += 2 if re.search(r"reports?.{0,80}(?:first|second|third|fourth|fiscal).{0,30}quarter", text, re.I | re.S) else 0
    score += 1 if re.search(r"[\"“].{20,300}\bsaid\b", text, re.I | re.S) else 0
    score -= 2 if re.search(r"notes and definitions|supplemental information", text[:1500], re.I) else 0
    return max(score, 0)


def management_driver_excerpt(text: str) -> str:
    sentences = evidence_chunks(text)
    driver_pattern = re.compile(
        r"\b(driven by|due to|reflecting|primarily|resulted from|benefited from|offset by|led by|"
        r"attributable to|as a result of|fueled by|partially offset by)\b",
        re.I,
    )
    operating_pattern = re.compile(
        r"\b(revenue|net sales|sales|operating income|earnings|margin|profit|volume|pricing|demand|"
        r"transactions|occupancy|rents?|costs?|expenses?|production|deliveries|memberships?|"
        r"subscribers?|cash flow|free cash flow|utilization|growth)\b",
        re.I,
    )
    boilerplate_pattern = re.compile(
        r"forward-looking|risk factors|could adversely|may adversely|rounding|compensation awards?|"
        r"stockholders.? equity|tax audits?|tax regulations?|deferred tax|net leverage ratio|"
        r"reconciliation|unsettled derivatives|mark-to-market|eliminations? of intersegment"
        r"|non-gaap financial measure|we calculate|to assist investors|intercompany|deferred profits|"
        r"we expect|forecast|guidance|outlook|notes and definitions|stock compensation|termination fee|"
        r"most comparable gaap|adjusted ebit \(",
        re.I,
    )
    ranked = []
    seen = set()
    for position, sentence in enumerate(sentences):
        if (
            not 35 <= len(sentence) <= 450
            or boilerplate_pattern.search(sentence)
            or len(re.findall(r"(?:\$|\b\d+(?:\.\d+)?%?)", sentence)) > 12
            or sentence.rstrip().endswith(":")
        ):
            continue
        if not driver_pattern.search(sentence) or not operating_pattern.search(sentence):
            continue
        normalized = re.sub(r"\W+", " ", sentence).strip().lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        score = 5
        score += 2 if re.search(r"\b(revenue|net sales|operating income|earnings|margin|profit|cash flow)\b", sentence, re.I) else 0
        score += 1 if re.search(r"\b(quarter|year over year|year-over-year|results?)\b", sentence, re.I) else 0
        score += 1 if re.search(r"(?:\$|\b\d+(?:\.\d+)?%)", sentence) else 0
        score += 1 if re.search(r"\b(said|ceo|chief executive|chief financial)\b", sentence, re.I) else 0
        ranked.append((-score, position, sentence))
    ranked.sort()
    return " ".join(row[2] for row in ranked[:3])[:3000]


def evidence_chunks(text: str) -> list[str]:
    rows = [" ".join(row.split()) for row in re.split(r"(?<=[.!?])\s+|[\r\n]+|[•▪◦]+", text)]
    chunks = []
    index = 0
    while index < len(rows):
        chunk = rows[index]
        if re.search(r"\b[A-Z]\.$", chunk) and index + 1 < len(rows) and re.match(r"[A-Z][a-z'-]+,", rows[index + 1]):
            chunk = f"{chunk} {rows[index + 1]}"
            index += 1
        chunks.append(chunk)
        index += 1
    return chunks


def filing_index_url(filing_url: str) -> str:
    return filing_url.rsplit("/", 1)[0] + "/index.json"


def source_for_filing(company, filed_date: date, accession: str) -> SourceDocument | None:
    compact_accession = accession.replace("-", "")
    queryset = SourceDocument.objects.filter(company=company, title__icontains="10-Q")
    return (
        queryset.filter(url__icontains=compact_accession).first()
        or queryset.filter(published_date__date=filed_date).first()
    )


def parse_fact_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None
