from django.urls import path

from apps.search import api


urlpatterns = [
    path("dashboard", api.dashboard, name="app-dashboard"),
    path("categories", api.categories, name="app-categories"),
    path("search", api.search, name="app-search"),
    path("search/suggest", api.search_suggest, name="app-search-suggest"),
]
