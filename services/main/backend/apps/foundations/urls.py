from django.urls import path

from apps.foundations import api


urlpatterns = [
    path("foundations/standards", api.foundation_standards, name="app-foundation-standards"),
]
