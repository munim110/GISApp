"""
Export endpoints.
- /api/export/image/  — screenshot of the map canvas (handled client-side via leaflet-image)
- /api/export/geotiff/<layer_id>/ — serve the original GeoTIFF
- /api/export/geojson/<layer_id>/ — serve GeoJSON (converted from any vector format)
"""
import os
from django.http import FileResponse, JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from apps.layers.models import Layer


@require_http_methods(["GET"])
def export_geotiff(request, layer_id):
    layer = get_object_or_404(Layer, id=layer_id, layer_type="raster")
    response = FileResponse(
        open(layer.file.path, "rb"),
        content_type="image/tiff",
        as_attachment=True,
        filename=f"{layer.name}.tif",
    )
    return response


@require_http_methods(["GET"])
def export_geojson(request, layer_id):
    layer = get_object_or_404(Layer, id=layer_id)

    if layer.geojson_cache:
        response = FileResponse(
            open(layer.geojson_cache.path, "rb"),
            content_type="application/geo+json",
            as_attachment=True,
            filename=f"{layer.name}.geojson",
        )
        return response
    elif layer.layer_type in ("geojson",):
        response = FileResponse(
            open(layer.file.path, "rb"),
            content_type="application/geo+json",
            as_attachment=True,
            filename=f"{layer.name}.geojson",
        )
        return response

    return JsonResponse({"error": "No GeoJSON available for this layer"}, status=404)
