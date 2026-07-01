from django.urls import path

from apps.ingestion import api


urlpatterns = [
    path("health", api.health, name="ingestion-health"),
    path("companies", api.companies, name="ingestion-companies"),
    path("companies/<slug:slug>/profile", api.company_profile, name="ingestion-company-profile"),
    path("companies/<slug:slug>/business-model", api.company_business_model, name="ingestion-company-business-model"),
    path("companies/<slug:slug>/operating-kpis", api.company_operating_kpis, name="ingestion-company-operating-kpis"),
    path("companies/<slug:slug>/management-promises", api.company_management_promises, name="ingestion-company-management-promises"),
    path("companies/<slug:slug>/strategy-milestones", api.company_strategy_milestones, name="ingestion-company-strategy-milestones"),
    path("companies/<slug:slug>/earnings", api.company_earnings, name="ingestion-company-earnings"),
    path("companies/<slug:slug>/capital-allocation", api.company_capital_allocation, name="ingestion-company-capital-allocation"),
    path("companies/<slug:slug>/competitive-position", api.company_competitive_position, name="ingestion-company-competitive-position"),
    path("companies/<slug:slug>/product-pricing", api.company_product_pricing, name="ingestion-company-product-pricing"),
    path("companies/<slug:slug>/acquisition-lifecycle", api.company_acquisition_lifecycle, name="ingestion-company-acquisition-lifecycle"),
    path("companies/<slug:slug>/customer-supplier-dependency", api.company_customer_supplier_dependency, name="ingestion-company-customer-supplier-dependency"),
    path("companies/<slug:slug>/geographic-expansion", api.company_geographic_expansion, name="ingestion-company-geographic-expansion"),
    path("companies/<slug:slug>/leadership-decisions", api.company_leadership_decisions, name="ingestion-company-leadership-decisions"),
    path("companies/<slug:slug>/ownership-insider", api.company_ownership_insider, name="ingestion-company-ownership-insider"),
    path("companies/<slug:slug>/valuation-context", api.company_valuation_context, name="ingestion-company-valuation-context"),
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
