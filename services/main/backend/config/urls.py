"""URL placeholders for the InfoDJ main backend."""

from django.contrib import admin
from django.conf import settings
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve


def health(_request):
    return JsonResponse({"service": "infodj-main-backend", "status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/app/health", health, name="app-health"),
    path("api/app/", include("apps.accounts.urls")),
    path("api/app/", include("apps.search.urls")),
    path("api/app/", include("apps.theses.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
