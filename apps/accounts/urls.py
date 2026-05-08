from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("logout/", views.logout_view, name="logout"),
    path("api/me/", views.me, name="me"),
    path("api/users/", views.list_users, name="user-list"),
    path("api/users/<int:user_id>/update/", views.update_user, name="user-update"),
]
