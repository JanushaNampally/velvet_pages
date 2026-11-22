import hmac

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.seed import seed_defaults

from .forms import CodeForm, ForgotForm, LoginForm, ResetForm, SetupForm
from .models import Owner
from .otp import hit, issue_otp, normalize_phone, verify_otp

BACKEND = "django.contrib.auth.backends.ModelBackend"


def _ip(request):
    return request.META.get("REMOTE_ADDR", "")


def _find_owner(identifier):
    identifier = (identifier or "").strip()
    if "@" in identifier:
        return Owner.objects.filter(email__iexact=identifier).first()
    phone = normalize_phone(identifier)
    return Owner.objects.filter(phone=phone).first() if phone else None


def _dev_code(phone):
    if settings.DEBUG and settings.OTP_BACKEND == "console":
        return cache.get(f"devcode:{phone}")      # dev convenience only; never shown when DEBUG=0
    return None


def setup_view(request):
    """One-time owner creation in the browser. Closed forever once an owner exists."""
    if Owner.objects.exists():
        return redirect("login")
    token_needed = bool(settings.SETUP_TOKEN)
    form = SetupForm(request.POST or None, require_token=token_needed)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        phone = normalize_phone(d["phone"])
        if not phone:
            form.add_error("phone", "Enter a valid phone number.")
        elif token_needed and not hmac.compare_digest(d["setup_token"], settings.SETUP_TOKEN):
            form.add_error("setup_token", "Wrong setup token.")
        else:
            owner = Owner(email=d["email"].lower(), phone=phone, display_name=d["display_name"])
            owner.set_password(d["password"])
            owner.save()
            seed_defaults()
            login(request, owner, backend=BACKEND)
            messages.success(request, "Welcome to Velvet Pages.")
            return redirect("dashboard")
    return render(request, "auth/setup.html", {"form": form})


def login_view(request):
    if not Owner.objects.exists():
        return redirect("setup")
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if hit(f"login-ip:{_ip(request)}", 15, 900):
            form.add_error(None, "Too many attempts. Wait 15 minutes and try again.")
        else:
            owner = _find_owner(form.cleaned_data["identifier"])
            if owner and owner.check_password(form.cleaned_data["password"]):
                if not settings.REQUIRE_OTP:
                    login(request, owner, backend=BACKEND)
                    return redirect("dashboard")
                if issue_otp(owner.phone, _ip(request)):
                    request.session["pending_owner"] = owner.pk
                    messages.info(request, "We sent a 6-digit code to your phone.")
                    return redirect("verify")
                form.add_error(None, "Too many codes requested. Try again in an hour.")
            else:
                form.add_error(None, "Wrong email/phone or password.")
    return render(request, "auth/login.html", {"form": form})


def verify_view(request):
    owner = Owner.objects.filter(pk=request.session.get("pending_owner")).first()
    if not owner:
        return redirect("login")
    form = CodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if hit(f"verify-ip:{_ip(request)}", 20, 3600):
            form.add_error(None, "Too many attempts. Try again later.")
        elif verify_otp(owner.phone, form.cleaned_data["code"]):
            request.session.pop("pending_owner", None)
            login(request, owner, backend=BACKEND)
            return redirect("dashboard")
        else:
            form.add_error(None, "Invalid or expired code.")
    return render(request, "auth/verify.html", {
        "form": form, "phone_hint": "•••••" + owner.phone[-3:], "dev_code": _dev_code(owner.phone)})


def forgot_view(request):
    form = ForgotForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        owner = _find_owner(form.cleaned_data["identifier"])
        if owner:
            issue_otp(owner.phone, _ip(request))
        request.session["reset_owner"] = owner.pk if owner else 0
        messages.info(request, "If that account exists, a code has been sent to its phone.")
        return redirect("reset")
    return render(request, "auth/forgot.html", {"form": form})


def reset_view(request):
    owner = Owner.objects.filter(pk=request.session.get("reset_owner")).first()
    if not owner:
        return redirect("forgot")
    form = ResetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if hit(f"reset-ip:{_ip(request)}", 10, 3600):
            form.add_error(None, "Too many attempts. Try again later.")
        elif verify_otp(owner.phone, form.cleaned_data["code"]):
            owner.set_password(form.cleaned_data["new_password"])
            owner.save(update_fields=["password"])
            request.session.pop("reset_owner", None)
            messages.success(request, "Password changed. Please log in.")
            return redirect("login")
        else:
            form.add_error("code", "Invalid or expired code.")
    return render(request, "auth/reset.html", {"form": form, "dev_code": _dev_code(owner.phone)})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("login")