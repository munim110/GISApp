from django.contrib import admin
from .models import Layer


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    list_display = ["name", "layer_type", "owner", "is_locked", "is_processed",
                    "visible", "z_index", "created_at"]
    list_filter = ["layer_type", "is_locked", "is_processed", "visible"]
    list_editable = ["is_locked", "visible"]
    search_fields = ["name", "owner__username"]
    readonly_fields = ["id", "created_at", "updated_at",
                       "bbox_west", "bbox_south", "bbox_east", "bbox_north"]
    fieldsets = (
        (None, {"fields": ("id", "name", "layer_type", "file", "owner", "is_locked")}),
        ("Display", {
            "fields": ("visible", "opacity", "z_index", "style_config",
                       "outline_color", "outline_weight", "outline_visible"),
        }),
        ("Bounds", {
            "fields": ("bbox_west", "bbox_south", "bbox_east", "bbox_north"),
        }),
        ("Processing", {
            "fields": ("is_processed", "processing_error", "geojson_cache",
                       "aux_files"),
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
