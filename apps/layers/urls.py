from django.urls import path
from . import views

urlpatterns = [
    path("", views.layer_list, name="layer-list"),
    path("upload/", views.layer_upload, name="layer-upload"),
    path("reorder/", views.layer_reorder, name="layer-reorder"),
    path("<uuid:layer_id>/", views.layer_detail, name="layer-detail"),
    path("<uuid:layer_id>/update/", views.layer_update, name="layer-update"),
    path("<uuid:layer_id>/delete/", views.layer_delete, name="layer-delete"),
    path("<uuid:layer_id>/pixel/", views.layer_pixel_stats, name="layer-pixel-stats"),
]
