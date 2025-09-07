from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("", include("claims.urls")),
    path("accounts/", include("django.contrib.auth.urls")),  # ← login/logout/password views
    path("admin/", admin.site.urls),
]
