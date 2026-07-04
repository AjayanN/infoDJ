from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def foundation_standards(_request):
    return Response(
        {
            "status": "available",
            "purpose": "Shared Phase 2 rules for evidence, claims, metrics, periods, company identity, confidence, review, state labels, and freshness.",
            "pilot": {
                "company_slug": "netflix",
                "company_name": "Netflix",
                "review_period_start": "2023-01-01",
                "review_period_end": "2026-06-30",
                "reason": "Netflix has broad coverage across filings, earnings, operating KPIs, strategy events, and consumer-facing product history.",
            },
            "rules": [
                {
                    "key": "evidence",
                    "label": "Evidence Rules",
                    "summary": "Prefer source-backed facts from filings, earnings releases, investor materials, official company sources, and reviewed ingestion records.",
                    "requirements": [
                        "Every material conclusion should expose a source label or source gap.",
                        "Derived values should preserve the original source input and calculation context.",
                        "Unsupported claims should remain unavailable instead of being inferred.",
                    ],
                },
                {
                    "key": "claims",
                    "label": "Claim Rules",
                    "summary": "Claims should carry speaker, date, scope, source, and review state where the feature evaluates statements or promises.",
                    "requirements": [
                        "Do not imply deception or intent without authoritative support.",
                        "Separate management statements, external evidence, outcomes, and user notes.",
                        "Preserve revisions and conflicting claims instead of overwriting them.",
                    ],
                },
                {
                    "key": "metrics",
                    "label": "Metric Rules",
                    "summary": "Metrics should expose definition, unit, period, source, comparability, and confidence.",
                    "requirements": [
                        "Do not treat unavailable numeric data as zero.",
                        "Flag changed metric definitions and non-comparable peer metrics.",
                        "Currency, segment, and reporting-scope differences should be visible.",
                    ],
                },
                {
                    "key": "periods",
                    "label": "Period Rules",
                    "summary": "Periods should distinguish announcement, effective, reporting, review, and updated-at dates.",
                    "requirements": [
                        "Show the date basis used by the feature.",
                        "Keep historical snapshots available when values can change over time.",
                        "Use explicit unavailable states when dates are not disclosed.",
                    ],
                },
                {
                    "key": "company_identity",
                    "label": "Company Identity Rules",
                    "summary": "Company records should use stable slugs and preserve source identifiers such as SEC CIK and Wikidata ID when available.",
                    "requirements": [
                        "Company slug is the API routing identity.",
                        "Display name, sector, country, SEC CIK, and Wikidata ID should remain visible when available.",
                        "Aliases, subsidiaries, and brands should not replace the parent company identity unless the feature explicitly tracks that relationship.",
                    ],
                },
                {
                    "key": "confidence",
                    "label": "Confidence Rules",
                    "summary": "Confidence should describe evidence quality and extraction reliability, not investment attractiveness.",
                    "requirements": [
                        "Low confidence should explain what is missing.",
                        "High confidence requires source-backed structured evidence.",
                        "Predictions, scenarios, and classifications must show assumptions.",
                    ],
                },
            ],
            "states": [
                {"key": "available", "label": "Available", "meaning": "Reviewed source-backed information is available for the selected scope."},
                {"key": "partial", "label": "Partial", "meaning": "Some source-backed information exists, but material fields or periods are missing."},
                {"key": "unavailable", "label": "Unavailable", "meaning": "No reviewed source-backed information is available for the selected scope."},
                {"key": "stale", "label": "Stale", "meaning": "Information exists but is older than the freshness expectation for its type."},
                {"key": "conflict", "label": "Conflict", "meaning": "Sources disagree or a later source materially changes an earlier claim."},
            ],
            "review_workflows": [
                {"key": "source_gap", "label": "Source Gap", "steps": ["Surface gap", "Route to ingestion", "Attach candidate source", "Promote only deterministic values", "Retain gap if evidence remains insufficient"]},
                {"key": "correction", "label": "Correction", "steps": ["Accept correction request", "Require better evidence", "Record reviewer note", "Preserve prior value in history", "Update visible state"]},
                {"key": "editorial_review", "label": "Editorial Review", "steps": ["Draft", "Needs evidence", "In review", "Reviewed", "Disputed or archived if challenged"]},
            ],
            "freshness": [
                {"information_type": "market_price", "expectation": "Refresh daily when market-data source is available."},
                {"information_type": "filing_fact", "expectation": "Refresh after SEC filing ingestion and preserve filing period."},
                {"information_type": "earnings_release", "expectation": "Refresh after quarterly release or source ingestion."},
                {"information_type": "profile_snapshot", "expectation": "Refresh daily when company-profile ingestion runs, but expose last reviewed timestamp."},
                {"information_type": "user_workspace", "expectation": "Update immediately when the authenticated user edits the workspace."},
                {"information_type": "reviewed_case_study", "expectation": "Refresh only through editorial review or correction workflow."},
            ],
        }
    )
