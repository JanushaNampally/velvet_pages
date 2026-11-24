from django.urls import path
from . import views

urlpatterns = [
    path("setup/", views.setup_view, name="setup"),
    path("setup/details/", views.setup_details_view, name="setup_details"),
    path("login/", views.login_view, name="login"),
    path("auth/google/start/", views.google_start, name="google_start"),
    path("auth/google/callback/", views.google_callback, name="google_callback"),
    path("logout/", views.logout_view, name="logout"),
]