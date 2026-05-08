"""
Auth views for SWAMP.

Roles:
- Admin / staff (is_staff or is_superuser): full control, can lock layers,
  can edit any layer regardless of lock state.
- Standard users (authenticated, not staff): can upload, edit, and delete
  their own (unlocked) layers. Can view all layers but cannot mutate
  layers owned by others or any locked layer.
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("viewer")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("viewer")
        error = "Invalid username or password."

    return render(request, "accounts/login.html", {"error": error})


@require_http_methods(["GET", "POST"])
def signup_view(request):
    if request.user.is_authenticated:
        return redirect("viewer")

    error = None
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        confirm = request.POST.get("confirm", "")
        email = request.POST.get("email", "").strip()

        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.objects.filter(username=username).exists():
            error = "Username is already taken."
        else:
            user = User.objects.create_user(
                username=username, password=password, email=email
            )
            login(request, user)
            return redirect("viewer")

    return render(request, "accounts/signup.html", {"error": error})


@require_http_methods(["GET", "POST"])
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
@require_http_methods(["GET"])
def me(request):
    u = request.user
    return JsonResponse({
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "is_staff": u.is_staff,
        "is_superuser": u.is_superuser,
        "role": "admin" if (u.is_staff or u.is_superuser) else "user",
    })


# -- Admin-only endpoints for user access management --

def _admin_required(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@require_http_methods(["GET"])
def list_users(request):
    if not _admin_required(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)
    users = User.objects.all().order_by("username")
    return JsonResponse({
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_staff": u.is_staff,
                "is_active": u.is_active,
            }
            for u in users
        ]
    })


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_user(request, user_id):
    if not _admin_required(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)
    import json
    try:
        u = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({"error": "not found"}, status=404)
    data = json.loads(request.body or "{}")
    if "is_staff" in data:
        u.is_staff = bool(data["is_staff"])
    if "is_active" in data:
        u.is_active = bool(data["is_active"])
    if data.get("password"):
        u.set_password(data["password"])
    u.save()
    return JsonResponse({"status": "ok"})
