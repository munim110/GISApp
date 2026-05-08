import json
import os
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

from .models import Layer
from .serializers import layer_to_dict
from .processing import process_layer


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@require_http_methods(["GET"])
def layer_list(request):
    layers = Layer.objects.all()
    return JsonResponse({
        "layers": [layer_to_dict(l, request.user) for l in layers]
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def layer_upload(request):
    name = request.POST.get("name", "").strip()
    uploaded_file = request.FILES.get("file")

    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    if not name:
        name = os.path.splitext(uploaded_file.name)[0]

    ext = os.path.splitext(uploaded_file.name)[1].lower()
    if ext in (".tif", ".tiff", ".img", ".vrt"):
        layer_type = Layer.LayerType.RASTER
    elif ext in (".geojson", ".json"):
        layer_type = Layer.LayerType.GEOJSON
    else:
        layer_type = Layer.LayerType.VECTOR

    # Only admins may pre-lock at upload time. Standard users always upload
    # unlocked layers owned by themselves.
    is_locked = False
    if _is_admin(request.user) and request.POST.get("is_locked") in ("1", "true", "True"):
        is_locked = True

    layer = Layer.objects.create(
        name=name,
        layer_type=layer_type,
        file=uploaded_file,
        owner=request.user,
        is_locked=is_locked,
    )

    process_layer(layer)
    layer.refresh_from_db()

    return JsonResponse({"layer": layer_to_dict(layer, request.user)}, status=201)


@login_required
@require_http_methods(["GET"])
def layer_detail(request, layer_id):
    layer = get_object_or_404(Layer, id=layer_id)
    return JsonResponse({"layer": layer_to_dict(layer, request.user)})


@csrf_exempt
@login_required
@require_http_methods(["PATCH"])
def layer_update(request, layer_id):
    layer = get_object_or_404(Layer, id=layer_id)
    data = json.loads(request.body or "{}")

    is_admin = _is_admin(request.user)

    if not layer.can_edit(request.user):
        # Allow even non-editors to toggle visibility per their own session,
        # but never persist changes to a locked layer.
        return JsonResponse(
            {"error": "This layer is locked. Only admins can modify it."},
            status=403,
        )

    if "name" in data:
        layer.name = data["name"]
    if "visible" in data:
        layer.visible = bool(data["visible"])
    if "opacity" in data:
        layer.opacity = float(data["opacity"])
    if "z_index" in data:
        layer.z_index = int(data["z_index"])
    if "style_config" in data:
        layer.style_config = {**layer.style_config, **data["style_config"]}
    if "outline_color" in data:
        layer.outline_color = data["outline_color"]
    if "outline_weight" in data:
        layer.outline_weight = float(data["outline_weight"])
    if "outline_visible" in data:
        layer.outline_visible = bool(data["outline_visible"])

    # Only admins may change lock state
    if "is_locked" in data and is_admin:
        layer.is_locked = bool(data["is_locked"])

    layer.save()
    return JsonResponse({"layer": layer_to_dict(layer, request.user)})


@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def layer_delete(request, layer_id):
    layer = get_object_or_404(Layer, id=layer_id)

    if not layer.can_edit(request.user):
        return JsonResponse(
            {"error": "Cannot delete a locked layer."},
            status=403,
        )

    if layer.file:
        try:
            os.remove(layer.file.path)
        except FileNotFoundError:
            pass
    if layer.geojson_cache:
        try:
            os.remove(layer.geojson_cache.path)
        except FileNotFoundError:
            pass
    layer.delete()
    return JsonResponse({"status": "deleted"})


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def layer_reorder(request):
    data = json.loads(request.body)
    order = data.get("order", [])
    is_admin = _is_admin(request.user)
    for item in order:
        try:
            layer = Layer.objects.get(id=item["id"])
        except Layer.DoesNotExist:
            continue
        if layer.is_locked and not is_admin:
            continue
        layer.z_index = item["z_index"]
        layer.save(update_fields=["z_index"])
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# Cursor / pixel statistics
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(["GET"])
def layer_pixel_stats(request, layer_id):
    """Return the pixel value at a given lat/lng for a raster layer.

    Query params: ?lat=<>&lng=<>
    Response: { value, values: [...per-band], pixel_area_m2,
                approx_pixel_area_km2, units }
    """
    import math
    layer = get_object_or_404(Layer, id=layer_id)
    if layer.layer_type != "raster":
        return JsonResponse({"error": "Pixel stats are only available for rasters."},
                            status=400)

    try:
        lat = float(request.GET.get("lat"))
        lng = float(request.GET.get("lng"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "lat and lng required"}, status=400)

    try:
        import rasterio
        from rasterio.transform import rowcol
    except ImportError:
        return JsonResponse({"error": "rasterio not installed"}, status=500)

    try:
        with rasterio.open(layer.file.path) as src:
            row, col = rowcol(src.transform, lng, lat)
            if row < 0 or col < 0 or row >= src.height or col >= src.width:
                return JsonResponse({"in_bounds": False})

            values = []
            for b in range(1, src.count + 1):
                window = ((row, row + 1), (col, col + 1))
                arr = src.read(b, window=window)
                v = arr[0, 0] if arr.size else None
                values.append(None if v is None else float(v))

            # Pixel size: assume EPSG:4326 (deg) — convert to metres at this lat
            px_w_deg = abs(src.transform.a)
            px_h_deg = abs(src.transform.e)
            # 1 deg lat ~= 111_320 m; 1 deg lng ~= 111_320 * cos(lat)
            m_per_deg_lat = 111_320.0
            m_per_deg_lng = 111_320.0 * max(math.cos(math.radians(lat)), 1e-9)
            px_w_m = px_w_deg * m_per_deg_lng
            px_h_m = px_h_deg * m_per_deg_lat
            pixel_area_m2 = px_w_m * px_h_m

            return JsonResponse({
                "in_bounds": True,
                "row": int(row),
                "col": int(col),
                "value": values[0] if values else None,
                "values": values,
                "band_count": src.count,
                "pixel_size_m": [px_w_m, px_h_m],
                "pixel_area_m2": pixel_area_m2,
                "pixel_area_km2": pixel_area_m2 / 1_000_000.0,
                "pixel_area_ha": pixel_area_m2 / 10_000.0,
                "units": "metres (approx., assuming EPSG:4326)",
            })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
