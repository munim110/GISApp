from django.urls import path
from . import views

urlpatterns = [
    path("geotiff/<uuid:layer_id>/", views.export_geotiff, name="export-geotiff"),
    path("geojson/<uuid:layer_id>/", views.export_geojson, name="export-geojson"),
]
