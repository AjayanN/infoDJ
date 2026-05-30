from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.ingestion.urls")),
    path("internal/", include("apps.ingestion.urls")),
]
