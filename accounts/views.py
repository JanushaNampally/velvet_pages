import hmac
import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.seed import seed_defaults

from . import google
from .forms import LoginForm, SetupForm
from .models import Owner
from .throttle import hit

BACKEND = "django.contrib.auth.backends.ModelBackend"


def _ip(request):
    return request.META.get("REMOTE_ADDR", "")


def _find_owner(identifier):
    identifier = (identifier or "").strip()
    if not identifier:
        return None
    if "@" in identifier:
        return Owner.objects.filter(email__iexact=identifier).first()
    return Owner.objects.filter(username__iexact=identifier).first()


# ---------------------------------------------------------------- registration
def setup_view(request):
    """Registration step 1: continue with Google. Open to anyone with a Google account."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "auth/setup.html", {"google_ready": google.is_configured()})


def setup_details_view(request):
    """Registration step 2: username, date of birth, password. Then go to login."""
    if request.user.is_authenticated:
        return redirect("dashboard")
    ident = request.session.get("google_identity")
    if not ident:
        return redirect("setup")
    invite_needed = bool(settings.SETUP_TOKEN)
    form = SetupForm(request.POST or None, require_token=invite_needed)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        if hit(f"register:{_ip(request)}", 10, 3600):
            form.add_error(None, "Too many attempts. Try again later.")
        elif invite_needed and not hmac.compare_digest(d["setup_token"].encode(), settings.SETUP_TOKEN.encode()):
            form.add_error("setup_token", "Wrong invite code.")
        else:
            owner = Owner(username=d["username"], email=ident["email"], google_sub=ident["sub"],
                          date_of_birth=d["date_of_birth"])
            owner.set_password(d["password"])
            try:
                with transaction.atomic():
                    owner.save()
            except IntegrityError:
                form.add_error("username", "That username is taken. Try another.")
            else:
                seed_defaults(owner)
                request.session.pop("google_identity", None)
                messages.success(request, "Account created. Please log in.")
                return redirect("login")
    return render(request, "auth/setup_details.html", {"form": form, "email": ident["email"]})


# ---------------------------------------------------------------- Google
def google_start(request):
    mode = "register" if request.GET.get("mode") == "register" else "login"
    back = "setup" if mode == "register" else "login"
    if not google.is_configured():
        messages.error(request, "Google sign-in is not configured yet (set GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET).")
        return redirect(back)
    state = secrets.token_urlsafe(32)
    request.session["google_state"] = state
    request.session["google_mode"] = mode
    return redirect(google.authorize_url(state))


def google_callback(request):
    state = request.session.pop("google_state", "")
    mode = request.session.pop("google_mode", "login")
    back = "setup" if mode == "register" else "login"
    if request.GET.get("error"):
        messages.error(request, "Google sign-in was cancelled.")
        return redirect(back)
    code = request.GET.get("code", "")
    if not state or not code or not hmac.compare_digest(state.encode(), request.GET.get("state", "").encode()):
        messages.error(request, "Sign-in session expired. Please try again.")
        return redirect(back)
    if hit(f"google-cb:{_ip(request)}", 20, 900):
        messages.error(request, "Too many attempts. Wait a few minutes.")
        return redirect(back)
    try:
        ident = google.get_identity(code)
    except Exception:
        messages.error(request, "Could not complete sign-in with Google. Please try again.")
        return redirect(back)
    if not ident["verified"] or not ident["email"]:
        messages.error(request, "Your Google email is not verified.")
        return redirect(back)

    existing = Owner.objects.filter(google_sub=ident["sub"]).first() or Owner.objects.filter(email=ident["email"]).first()
    if mode == "register":
        if existing:
            messages.info(request, "That Google account already has an account. Please log in.")
            return redirect("login")
        request.session["google_identity"] = {"sub": ident["sub"], "email": ident["email"]}
        return redirect("setup_details")

    if not existing or existing.google_sub != ident["sub"]:
        messages.error(request, "No account for that Google account yet. Create one first.")
        return redirect("setup")
    login(request, existing, backend=BACKEND)
    request.session["auth_via"] = "google"
    return redirect("dashboard")


# ---------------------------------------------------------------- login / logout
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if hit(f"login-ip:{_ip(request)}", 15, 900):
            form.add_error(None, "Too many attempts. Wait 15 minutes and try again.")
        else:
            owner = _find_owner(form.cleaned_data["identifier"])
            if owner and owner.check_password(form.cleaned_data["password"]):
                login(request, owner, backend=BACKEND)
                request.session["auth_via"] = "password"
                return redirect("dashboard")
            form.add_error(None, "Wrong username/email or password.")
    return render(request, "auth/login.html", {"form": form, "google_ready": google.is_configured()})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")