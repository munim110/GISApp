from django.db import models
from django.conf import settings
import uuid
import os


def layer_upload_path(instance, filename):
    return f"layers/{instance.id}/{filename}"


class Layer(models.Model):
    class LayerType(models.TextChoices):
        RASTER = "raster", "Raster (GeoTIFF/IMG)"
        VECTOR = "vector", "Vector (SHP/GeoJSON/KML)"
        GEOJSON = "geojson", "GeoJSON"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    layer_type = models.CharField(max_length=20, choices=LayerType.choices)
    file = models.FileField(upload_to=layer_upload_path)
    aux_files = models.JSONField(default=list, blank=True)

    # Bounding box (WGS84)
    bbox_west = models.FloatField(null=True, blank=True)
    bbox_south = models.FloatField(null=True, blank=True)
    bbox_east = models.FloatField(null=True, blank=True)
    bbox_north = models.FloatField(null=True, blank=True)

    # Display config
    opacity = models.FloatField(default=1.0)
    visible = models.BooleanField(default=True)
    z_index = models.IntegerField(default=0)
    style_config = models.JSONField(default=dict, blank=True)
    # Always-visible boundary outline (rendered even when raster opacity is low)
    outline_color = models.CharField(max_length=20, default="#29b6f6")
    outline_weight = models.FloatField(default=2.0)
    outline_visible = models.BooleanField(default=True)

    # Ownership & access
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_layers",
    )
    # If True, only admins / staff can edit style, opacity, visibility,
    # delete or replace the layer. Other users may toggle it on/off in their
    # own session view but the persisted settings are immutable.
    is_locked = models.BooleanField(
        default=False,
        help_text="When locked, only admins can change style/opacity/etc.",
    )

    # Processing state
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)
    geojson_cache = models.FileField(
        upload_to="layers/cache/", null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["z_index", "created_at"]

    def __str__(self):
        return f"{self.name} ({self.layer_type})"

    @property
    def bbox(self):
        if None in (self.bbox_west, self.bbox_south, self.bbox_east, self.bbox_north):
            return None
        return [self.bbox_west, self.bbox_south, self.bbox_east, self.bbox_north]

    def file_extension(self):
        _, ext = os.path.splitext(self.file.name)
        return ext.lower()

    def can_edit(self, user):
        """Permission check used by views for locked layers."""
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        if self.is_locked:
            return False
        return self.owner_id is None or self.owner_id == user.id
