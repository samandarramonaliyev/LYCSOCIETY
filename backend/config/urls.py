from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "LYC Society administration"
admin.site.site_title = "LYC Society admin"
admin.site.index_title = "LYC Society administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.common.urls")),
    path("api/v1/auth/", include("apps.identity.urls")),
    path("api/v1/verification/", include("apps.lyceums.urls")),
    path("api/v1/", include("apps.profiles.urls")),
    path("api/v1/", include("apps.clubs.urls")),
]
