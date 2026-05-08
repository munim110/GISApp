"""
Layer file processing — extracts bbox, converts to GeoJSON for vectors,
validates rasters. Runs after upload.
"""
import json
import os
import tempfile
import zipfile
from pathlib import Path


def process_layer(layer):
    """Entry point: dispatch to raster or vector processor."""
    ext = layer.file_extension()
    try:
        if ext in (".tif", ".tiff", ".img", ".vrt"):
            _process_raster(layer)
        elif ext in (".geojson", ".json"):
            _process_geojson(layer)
        elif ext == ".zip":
            _process_shapefile_zip(layer)
        elif ext == ".kml":
            _process_kml(layer)
        elif ext == ".shp":
            _process_shp(layer)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        layer.is_processed = True
        layer.processing_error = ""
    except Exception as e:
        layer.is_processed = False
        layer.processing_error = str(e)
    finally:
        layer.save()


# ---------------------------------------------------------------------------
# Raster
# ---------------------------------------------------------------------------

def _process_raster(layer):
    import rasterio
    from rasterio.warp import calculate_default_transform, reproject, transform_bounds, Resampling
    from rasterio.crs import CRS
    import numpy as np

    target_crs = CRS.from_epsg(4326)

    with rasterio.open(layer.file.path) as src:
        src_crs = src.crs or target_crs
        bounds = src.bounds
        west, south, east, north = transform_bounds(
            src_crs, "EPSG:4326", bounds.left, bounds.bottom, bounds.right, bounds.top
        )

        needs_reproject = src_crs and src_crs.to_epsg() not in (4326, 3857)

        if needs_reproject:
            transform, width, height = calculate_default_transform(
                src_crs, target_crs, src.width, src.height, *src.bounds
            )
            profile = src.meta.copy()
            profile.update(
                crs=target_crs,
                transform=transform,
                width=width,
                height=height,
            )

            # Reproject to a new file alongside the original
            reprojected_path = layer.file.path.replace(".tif", "_4326.tif").replace(".tiff", "_4326.tiff").replace(".img", "_4326.tif")
            if reprojected_path == layer.file.path:
                reprojected_path = layer.file.path + "_4326.tif"

            with rasterio.open(reprojected_path, "w", **profile) as dst:
                for i in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, i),
                        destination=rasterio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src_crs,
                        dst_transform=transform,
                        dst_crs=target_crs,
                        resampling=Resampling.nearest,
                    )

            # Replace the stored file with the reprojected version
            import os
            from django.core.files import File
            with open(reprojected_path, "rb") as f:
                new_name = os.path.basename(reprojected_path)
                layer.file.save(new_name, File(f), save=False)
            os.remove(reprojected_path)

        band_count = src.count
        dtype = str(src.dtypes[0])
        nodata = src.nodatavals[0] if src.nodatavals else None

        # Compute per-band min/max from a downsampled overview so we have
        # sensible defaults for color ramps. Read at most ~256x256 samples.
        band_stats = []
        max_dim = 256
        scale = max(1, max(src.width, src.height) // max_dim)
        out_w = max(1, src.width // scale)
        out_h = max(1, src.height // scale)
        for b in range(1, band_count + 1):
            try:
                arr = src.read(b, out_shape=(out_h, out_w),
                               resampling=Resampling.average)
                if nodata is not None:
                    arr = arr[arr != nodata]
                arr = arr[np.isfinite(arr)] if arr.size else arr
                if arr.size:
                    band_stats.append({
                        "min": float(np.min(arr)),
                        "max": float(np.max(arr)),
                        "mean": float(np.mean(arr)),
                    })
                else:
                    band_stats.append({"min": 0.0, "max": 1.0, "mean": 0.5})
            except Exception:
                band_stats.append({"min": 0.0, "max": 1.0, "mean": 0.5})

    layer.bbox_west = west
    layer.bbox_south = south
    layer.bbox_east = east
    layer.bbox_north = north
    layer.layer_type = "raster"

    layer.style_config = {
        **layer.style_config,
        "band_count": band_count,
        "dtype": dtype,
        "crs": "EPSG:4326",
        "reprojected": needs_reproject,
        "nodata": None if nodata is None else float(nodata),
        "band_stats": band_stats,
        # Visualization defaults — overridden by user settings later.
        "render_mode": "single" if band_count == 1 else "rgb",
        "single_band": 1,
        "rgb_bands": [1, min(2, band_count), min(3, band_count)],
        "color_ramp": "viridis",
    }


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------

def _process_geojson(layer):
    import json

    with open(layer.file.path, "r") as f:
        gj = json.load(f)

    west, south, east, north = _bbox_from_geojson(gj)
    layer.bbox_west = west
    layer.bbox_south = south
    layer.bbox_east = east
    layer.bbox_north = north
    layer.layer_type = "geojson"
    layer.geojson_cache = layer.file  # already GeoJSON


def _bbox_from_geojson(gj):
    coords = []
    _collect_coords(gj, coords)
    if not coords:
        return -180, -90, 180, 90
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lons), min(lats), max(lons), max(lats)


def _collect_coords(obj, out):
    if isinstance(obj, dict):
        t = obj.get("type")
        if t == "Point":
            out.append(obj["coordinates"])
        elif t in ("LineString", "MultiPoint"):
            out.extend(obj["coordinates"])
        elif t in ("Polygon", "MultiLineString"):
            for ring in obj["coordinates"]:
                out.extend(ring)
        elif t == "MultiPolygon":
            for poly in obj["coordinates"]:
                for ring in poly:
                    out.extend(ring)
        elif t == "GeometryCollection":
            for g in obj.get("geometries", []):
                _collect_coords(g, out)
        elif t == "Feature":
            _collect_coords(obj.get("geometry"), out)
        elif t == "FeatureCollection":
            for f in obj.get("features", []):
                _collect_coords(f, out)
    elif obj is None:
        pass


# ---------------------------------------------------------------------------
# Shapefile (as .zip bundle)
# ---------------------------------------------------------------------------

def _process_shapefile_zip(layer):
    import fiona
    from fiona.transform import transform_geom
    import json

    zip_path = layer.file.path
    extract_dir = Path(zip_path).parent / "extracted"
    extract_dir.mkdir(exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise ValueError("No .shp file found in zip archive")

    _convert_shp_to_geojson(layer, str(shp_files[0]))


def _process_shp(layer):
    _convert_shp_to_geojson(layer, layer.file.path)


def _convert_shp_to_geojson(layer, shp_path):
    import fiona
    from fiona.transform import transform_geom
    import json
    from django.core.files.base import ContentFile

    features = []
    west, south, east, north = 180, 90, -180, -90

    with fiona.open(shp_path) as src:
        src_crs = src.crs_wkt or "EPSG:4326"
        for feature in src:
            geom = {k: v for k, v in dict(transform_geom(src_crs, "EPSG:4326", feature["geometry"])).items() if v is not None}
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": dict(feature["properties"]),
            })
        # Use fiona's bounds
        if src.bounds:
            b = src.bounds
            import pyproj
            transformer = pyproj.Transformer.from_crs(
                src_crs, "EPSG:4326", always_xy=True
            )
            west, south = transformer.transform(b[0], b[1])
            east, north = transformer.transform(b[2], b[3])

    geojson = {"type": "FeatureCollection", "features": features}
    geojson_str = json.dumps(geojson)

    cache_name = f"layers/cache/{layer.id}.geojson"
    layer.geojson_cache.save(cache_name, ContentFile(geojson_str.encode()), save=False)

    layer.bbox_west = west
    layer.bbox_south = south
    layer.bbox_east = east
    layer.bbox_north = north
    layer.layer_type = "vector"


# ---------------------------------------------------------------------------
# KML
# ---------------------------------------------------------------------------

def _process_kml(layer):
    import fiona
    _convert_shp_to_geojson.__doc__  # just ensure fiona imported
    # fiona can read KML with the KML driver
    import json
    from django.core.files.base import ContentFile

    features = []
    with fiona.open(layer.file.path, driver="KML") as src:
        for feature in src:
            geom = {k: v for k, v in dict(feature["geometry"]).items() if v is not None}
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": dict(feature["properties"]),
            })
        b = src.bounds

    geojson = {"type": "FeatureCollection", "features": features}
    cache_name = f"layers/cache/{layer.id}.geojson"
    layer.geojson_cache.save(
        cache_name, ContentFile(json.dumps(geojson).encode()), save=False
    )
    layer.bbox_west, layer.bbox_south, layer.bbox_east, layer.bbox_north = b
    layer.layer_type = "vector"
