from django.urls import path

from apps.search import api


urlpatterns = [
    path("dashboard", api.dashboard, name="app-dashboard"),
    path("categories", api.categories, name="app-categories"),
    path("search", api.search, name="app-search"),
    path("search/suggest", api.search_suggest, name="app-search-suggest"),
    path("companies/<slug:slug>/profile", api.company_profile, name="app-company-profile"),
    path("companies/<slug:slug>/business-model", api.company_business_model, name="app-company-business-model"),
    path("companies/<slug:slug>/operating-kpis", api.company_operating_kpis, name="app-company-operating-kpis"),
    path("companies/<slug:slug>/management-promises", api.company_management_promises, name="app-company-management-promises"),
    path("companies/<slug:slug>/strategy-milestones", api.company_strategy_milestones, name="app-company-strategy-milestones"),
    path("companies/<slug:slug>/earnings", api.company_earnings, name="app-company-earnings"),
    path("companies/<slug:slug>/capital-allocation", api.company_capital_allocation, name="app-company-capital-allocation"),
    path("companies/<slug:slug>/competitive-position", api.company_competitive_position, name="app-company-competitive-position"),
    path("companies/<slug:slug>/product-pricing", api.company_product_pricing, name="app-company-product-pricing"),
    path("companies/<slug:slug>/acquisition-lifecycle", api.company_acquisition_lifecycle, name="app-company-acquisition-lifecycle"),
    path("companies/<slug:slug>/customer-supplier-dependency", api.company_customer_supplier_dependency, name="app-company-customer-supplier-dependency"),
    path("companies/<slug:slug>/geographic-expansion", api.company_geographic_expansion, name="app-company-geographic-expansion"),
    path("companies/<slug:slug>/leadership-decisions", api.company_leadership_decisions, name="app-company-leadership-decisions"),
    path("companies/<slug:slug>/ownership-insider", api.company_ownership_insider, name="app-company-ownership-insider"),
    path("companies/<slug:slug>/valuation-context", api.company_valuation_context, name="app-company-valuation-context"),
    path("companies/<slug:slug>/regulatory-litigation", api.company_regulatory_litigation, name="app-company-regulatory-litigation"),
    path("companies/<slug:slug>/sector-themes", api.company_sector_themes, name="app-company-sector-themes"),
]
