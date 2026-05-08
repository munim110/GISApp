def layer_to_dict(layer, request_user=None):
    can_edit = layer.can_edit(request_user) if request_user is not None else True
    return {
        "id": str(layer.id),
        "name": layer.name,
        "type": layer.layer_type,
        "visible": layer.visible,
        "opacity": layer.opacity,
        "z_index": layer.z_index,
        "bbox": layer.bbox,
        "style_config": layer.style_config,
        "outline_color": layer.outline_color,
        "outline_weight": layer.outline_weight,
        "outline_visible": layer.outline_visible,
        "is_locked": layer.is_locked,
        "owner_id": layer.owner_id,
        "owner_username": layer.owner.username if layer.owner else None,
        "can_edit": can_edit,
        "is_processed": layer.is_processed,
        "processing_error": layer.processing_error,
        "file_url": layer.file.url if layer.file else None,
        "geojson_url": layer.geojson_cache.url if layer.geojson_cache else None,
        "created_at": layer.created_at.isoformat(),
    }
