from django.urls import path

from apps.ingestion import api


urlpatterns = [
    path("health", api.health, name="ingestion-health"),
    path("companies", api.companies, name="ingestion-companies"),
    path("companies/<slug:slug>/profile", api.company_profile, name="ingestion-company-profile"),
    path("dashboard-data", api.dashboard_data, name="ingestion-dashboard-data"),
    path("search", api.search, name="ingestion-search"),
    path("search/suggest", api.search_suggest, name="ingestion-search-suggest"),
    path("companies/<slug:slug>/events", api.company_events, name="ingestion-company-events"),
    path(
        "companies/<slug:slug>/strategic-turns",
        api.company_strategic_turns,
        name="ingestion-company-strategic-turns",
    ),
    path("jobs", api.jobs, name="ingestion-jobs"),
    path("source-gaps", api.source_gaps, name="ingestion-source-gaps"),
    path("jobs/<int:job_id>", api.job_detail, name="ingestion-job-detail"),
    path("jobs/daily-update", api.run_daily_update, name="ingestion-daily-update"),
    path("companies/<slug:slug>/refresh", api.refresh_company, name="ingestion-company-refresh"),
]
