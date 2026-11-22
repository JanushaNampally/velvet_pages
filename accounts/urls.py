from django.urls import path
from . import views

urlpatterns = [
    path("setup/", views.setup_view, name="setup"),
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_view, name="verify"),
    path("forgot/", views.forgot_view, name="forgot"),
    path("reset/", views.reset_view, name="reset"),
    path("logout/", views.logout_view, name="logout"),
]