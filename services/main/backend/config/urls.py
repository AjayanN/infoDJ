"""URL placeholders for the InfoDJ main backend."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path


def health(_request):
    return JsonResponse({"service": "infodj-main-backend", "status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/app/health", health, name="app-health"),
]
