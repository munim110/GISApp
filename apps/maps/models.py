from django.db import models


class SavedView(models.Model):
    name = models.CharField(max_length=255)
    center_lat = models.FloatField(default=23.685)
    center_lng = models.FloatField(default=90.356)
    zoom = models.IntegerField(default=7)
    base_layer = models.CharField(max_length=50, default="osm")
    layer_state = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
