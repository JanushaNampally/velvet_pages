from django.conf import settings
from django.shortcuts import redirect

PUBLIC = {"/login/", "/setup/", "/setup/details/", "/auth/google/start/", "/auth/google/callback/"}
class OwnerOnlyMiddleware:
    """Everything except the login pages requires the owner to be logged in."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path.startswith(settings.STATIC_URL):
            return self.get_response(request)
        if path not in PUBLIC and not request.user.is_authenticated:
            return redirect("/login/")
        response = self.get_response(request)
        response["Cache-Control"] = "no-store, private"
        response["Referrer-Policy"] = "same-origin"
        response["X-Robots-Tag"] = "noindex, nofollow"
        return response