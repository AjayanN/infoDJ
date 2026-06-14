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
    path("companies/<slug:slug>/earnings", api.company_earnings, name="app-company-earnings"),
]
