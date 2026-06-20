from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    dashboard_params = {"limit": request.GET.get("limit") or 12}
    for key in ("section", "page", "company"):
        if request.GET.get(key):
            dashboard_params[key] = request.GET[key]
    with ThreadPoolExecutor(max_workers=3) as executor:
        companies_future = executor.submit(ingestion_get, "companies")
        jobs_future = executor.submit(ingestion_get, "jobs", {"limit": 10})
        dashboard_future = executor.submit(ingestion_get, "dashboard-data", dashboard_params)
        companies_response, companies_error = companies_future.result()
        jobs_response, jobs_error = jobs_future.result()
        dashboard_data_response, dashboard_data_error = dashboard_future.result()

    companies = companies_response.get("companies", []) if companies_response else []
    jobs = jobs_response.get("jobs", []) if jobs_response else []
    dashboard_data = dashboard_data_response or empty_dashboard_data()
    sector_counts = build_sector_counts(companies)
    source_gaps = build_dashboard_source_gaps(companies, companies_error, jobs_error)
    source_gaps.extend(normalize_source_gaps(dashboard_data.get("source_gaps", [])))
    if dashboard_data_error:
        source_gaps.append(
            {
                "key": "dashboard_data_unavailable",
                "label": "Dashboard data unavailable",
                "reason": dashboard_data_error,
                "source": "ingestion.dashboard-data",
                "next_action": "Restore the ingestion dashboard-data API before rendering dashboard surfaces.",
            }
        )

    return Response(
        {
            "summary": {
                "company_count": len(companies),
                "source_count": sum_int(companies, "source_count"),
                "event_count": sum_int(companies, "event_count"),
                "strategic_turn_count": sum_int(companies, "strategic_turn_count"),
                "sector_count": len(sector_counts),
            },
            "sector_counts": sector_counts,
            "top_companies": sorted(
                companies,
                key=lambda row: (safe_int(row.get("event_count")), safe_int(row.get("strategic_turn_count"))),
                reverse=True,
            )[:10],
            "latest_jobs": jobs[:10],
            "ingestion": {
                "available": not companies_error and not dashboard_data_error,
                "companies_error": companies_error,
                "jobs_error": jobs_error,
                "dashboard_data_error": dashboard_data_error,
            },
            "source_gaps": source_gaps,
            "dashboards": dashboard_data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def categories(_request):
    companies_response, error = ingestion_get("companies")
    companies = companies_response.get("companies", []) if companies_response else []
    return Response(
        {
            "categories": build_sector_counts(companies),
            "ingestion": {
                "available": not error,
                "error": error,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search(request):
    query = normalized_query(request)
    if not query:
        return Response({"error": "q is required"}, status=400)
    params = {
        "q": query,
        "language": request.GET.get("language") or "en",
        "limit": request.GET.get("limit") or 10,
    }
    for key in ("company_page", "event_page", "turn_page"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get("search", params)
    if error:
        return Response({"error": "ingestion search unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_suggest(request):
    query = normalized_query(request)
    if not query:
        return Response({"error": "q is required"}, status=400)
    payload, error = ingestion_get("search/suggest", {"q": query, "language": request.GET.get("language") or "en"})
    if error:
        return Response({"error": "ingestion suggestions unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_profile(request, slug: str):
    params = {"as_of": request.GET["as_of"]} if request.GET.get("as_of") else None
    payload, error = ingestion_get(f"companies/{slug}/profile", params)
    if error:
        return Response({"error": "company profile unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_business_model(request, slug: str):
    params = {}
    for key in ("as_of", "compare_to"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/business-model", params or None)
    if error:
        return Response({"error": "business model unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_operating_kpis(request, slug: str):
    params = {}
    for key in ("metric", "segment", "geography", "start", "end", "comparable_only"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/operating-kpis", params or None)
    if error:
        return Response({"error": "operating KPIs unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_management_promises(request, slug: str):
    params = {}
    for key in ("status", "type", "due", "as_of", "promise"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/management-promises", params or None)
    if error:
        return Response({"error": "management promises unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_strategy_milestones(request, slug: str):
    params = {}
    for key in ("status", "type", "origin", "view", "milestone"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/strategy-milestones", params or None)
    if error:
        return Response({"error": "strategy milestones unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_earnings(request, slug: str):
    params = {"period": request.GET["period"]} if request.GET.get("period") else None
    payload, error = ingestion_get(f"companies/{slug}/earnings", params)
    if error:
        return Response({"error": "earnings intelligence unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_capital_allocation(request, slug: str):
    params = {"period": request.GET["period"]} if request.GET.get("period") else None
    payload, error = ingestion_get(f"companies/{slug}/capital-allocation", params)
    if error:
        return Response({"error": "capital allocation unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_competitive_position(request, slug: str):
    params = {}
    for key in ("as_of", "relationship"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/competitive-position", params or None)
    if error:
        return Response({"error": "competitive position unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_product_pricing(request, slug: str):
    params = {}
    for key in ("as_of", "type"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/product-pricing", params or None)
    if error:
        return Response({"error": "product and pricing history unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_acquisition_lifecycle(request, slug: str):
    params = {}
    for key in ("stage", "transaction_type", "outcome", "deal"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/acquisition-lifecycle", params or None)
    if error:
        return Response({"error": "acquisition lifecycle unavailable", "detail": error}, status=503)
    return Response(payload)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def company_customer_supplier_dependency(request, slug: str):
    params = {}
    for key in ("as_of", "type", "confidence"):
        if request.GET.get(key):
            params[key] = request.GET[key]
    payload, error = ingestion_get(f"companies/{slug}/customer-supplier-dependency", params or None)
    if error:
        return Response({"error": "customer and supplier dependency unavailable", "detail": error}, status=503)
    return Response(payload)


def ingestion_get(path: str, params: dict[str, object] | None = None) -> tuple[dict | None, str]:
    base_url = settings.INGESTION_API_URL.rstrip("/") + "/"
    url = urljoin(base_url, path)
    try:
        response = requests.get(url, params=params, timeout=INGESTION_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json(), ""
    except requests.RequestException as exc:
        return None, str(exc)
    except ValueError as exc:
        return None, f"Invalid JSON from ingestion service: {exc}"


def build_sector_counts(companies: list[dict]) -> list[dict]:
    sectors: dict[str, dict] = defaultdict(
        lambda: {
            "sector": "Unclassified",
            "company_count": 0,
            "source_count": 0,
            "event_count": 0,
            "strategic_turn_count": 0,
        }
    )
    for company in companies:
        sector_name = (company.get("sector") or "Unclassified").strip() or "Unclassified"
        sector = sectors[sector_name]
        sector["sector"] = sector_name
        sector["company_count"] += 1
        sector["source_count"] += safe_int(company.get("source_count"))
        sector["event_count"] += safe_int(company.get("event_count"))
        sector["strategic_turn_count"] += safe_int(company.get("strategic_turn_count"))
    return sorted(sectors.values(), key=lambda row: (-row["event_count"], row["sector"]))


def build_dashboard_source_gaps(companies: list[dict], companies_error: str, jobs_error: str) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    if companies_error:
        gaps.append(
            {
                "key": "companies_ingestion_unavailable",
                "label": "Company coverage unavailable",
                "reason": companies_error,
                "source": "ingestion.companies",
                "next_action": "Run or restore the ingestion companies API before showing dashboard coverage.",
            }
        )
    elif not companies:
        gaps.append(
            {
                "key": "companies_not_ingested",
                "label": "Company coverage unavailable",
                "reason": "No source-backed companies were returned by ingestion.",
                "source": "ingestion.companies",
                "next_action": "Run company metadata and source discovery ingestion.",
            }
        )
    if jobs_error:
        gaps.append(
            {
                "key": "ingestion_jobs_unavailable",
                "label": "Ingestion job history unavailable",
                "reason": jobs_error,
                "source": "ingestion.jobs",
                "next_action": "Restore the ingestion jobs API to show source refresh status.",
            }
        )
    missing_source_rows = [
        company.get("name") or company.get("slug") or "Unknown company"
        for company in companies
        if safe_int(company.get("source_count")) == 0
    ]
    if missing_source_rows:
        examples = ", ".join(str(name) for name in missing_source_rows[:3])
        suffix = f" and {len(missing_source_rows) - 3} more" if len(missing_source_rows) > 3 else ""
        gaps.append(
            {
                "key": "companies_missing_sources",
                "label": "Some companies have no source documents",
                "reason": f"{len(missing_source_rows)} companies returned without source documents: {examples}{suffix}.",
                "source": "ingestion.source_documents",
                "next_action": "Run source discovery for companies with zero source_count.",
            }
        )
    return gaps


def empty_dashboard_data() -> dict:
    sections = {
        key: empty_dashboard_section(key)
        for key in (
            "latest_moves",
            "strategic_turns",
            "patterns",
            "risk_signals",
            "turn_impact",
            "scorecards",
            "compare",
            "company_situations",
        )
    }
    return {
        "scope": None,
        "latest_events": [],
        "latest_turns": [],
        "patterns": [],
        "risk_signals": [],
        "turn_impact": [],
        "source_confidence": {
            "events": {"total": 0, "with_date": 0, "with_source": 0, "avg_confidence": 0},
            "turns": {"total": 0, "published": 0, "avg_confidence": 0},
            "source_types": [],
            "source_statuses": [],
            "event_reviews": [],
            "market_prices": {"total": 0, "companies": 0, "latest_price_date": None},
            "financial_facts": {"total": 0, "companies": 0, "latest_filed": None},
        },
        "scorecard_candidates": [],
        "company_situations": [],
        "compare_examples": [],
        "source_gaps": [],
        "sections": sections,
    }


def empty_dashboard_section(key: str) -> dict:
    return {
        "key": key,
        "status": "unavailable",
        "eligible_count": 0,
        "raw_count": 0,
        "excluded_count": 0,
        "items": [],
        "source_gaps": [],
        "required_data": [],
        "next_action": "Restore ingestion dashboard-data before rendering this dashboard.",
    }


def normalize_source_gaps(gaps: list[dict]) -> list[dict[str, str]]:
    normalized = []
    for gap in gaps:
        key = str(gap.get("key") or gap.get("gap_type") or "dashboard_gap")
        source = str(gap.get("source") or gap.get("provider") or "ingestion.dashboard-data")
        label = str(gap.get("label") or key.replace("_", " ").title())
        normalized.append(
            {
                "key": key,
                "label": label,
                "dashboard": str(gap.get("dashboard") or ""),
                "reason": str(gap.get("reason") or "Dashboard data is not eligible for display."),
                "source": source,
                "next_action": str(gap.get("next_action") or gap.get("next_ingestion_task") or ""),
            }
        )
    return normalized


def sum_int(rows: list[dict], key: str) -> int:
    return sum(safe_int(row.get(key)) for row in rows)


def safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalized_query(request) -> str:
    return " ".join((request.GET.get("q") or "").strip().split())
