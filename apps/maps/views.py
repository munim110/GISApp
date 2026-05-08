from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from apps.layers.models import Layer
from apps.layers.serializers import layer_to_dict
import json


@login_required
def viewer(request):
    layers = Layer.objects.all()
    layers_json = json.dumps([layer_to_dict(l, request.user) for l in layers])
    user = request.user
    user_json = json.dumps({
        "id": user.id,
        "username": user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "role": "admin" if (user.is_staff or user.is_superuser) else "user",
    })
    return render(request, "viewer.html", {
        "layers_json": layers_json,
        "user_json": user_json,
    })
