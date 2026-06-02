from __future__ import annotations

from collections import defaultdict
from urllib.parse import urljoin

import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


INGESTION_TIMEOUT_SECONDS = 10


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(_request):
    companies_response, companies_error = ingestion_get("companies")
    jobs_response, jobs_error = ingestion_get("jobs", {"limit": 10})

    companies = companies_response.get("companies", []) if companies_response else []
    jobs = jobs_response.get("jobs", []) if jobs_response else []
    sector_counts = build_sector_counts(companies)

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
                "available": not companies_error,
                "companies_error": companies_error,
                "jobs_error": jobs_error,
            },
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
    payload, error = ingestion_get("search", {"q": query, "language": request.GET.get("language") or "en"})
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


def sum_int(rows: list[dict], key: str) -> int:
    return sum(safe_int(row.get(key)) for row in rows)


def safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def normalized_query(request) -> str:
    return " ".join((request.GET.get("q") or "").strip().split())
