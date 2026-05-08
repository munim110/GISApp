from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.accounts.urls")),
    path("", include("apps.maps.urls")),
    path("api/layers/", include("apps.layers.urls")),
    path("api/export/", include("apps.exports.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
