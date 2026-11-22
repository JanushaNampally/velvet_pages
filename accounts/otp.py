import base64
import hashlib
import hmac
import logging
import re
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from .models import OTPCode

log = logging.getLogger(__name__)


def normalize_phone(raw):
    s = re.sub(r"[\s\-\(\)\.]", "", raw or "")
    if re.fullmatch(r"\d{10}", s):
        s = settings.DEFAULT_COUNTRY_CODE + s
    elif re.fullmatch(r"\d{11,15}", s):
        s = "+" + s
    return s if re.fullmatch(r"\+\d{10,15}", s) else None


def hit(key, limit, window):
    """Count an attempt; return True when the caller is OVER the limit."""
    if cache.add(key, 1, window):
        return False
    try:
        return cache.incr(key) > limit
    except ValueError:
        cache.set(key, 1, window)
        return False


def _hash(phone, code):
    return hmac.new(settings.SECRET_KEY.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def _deliver(phone, code):
    if settings.OTP_BACKEND == "twilio":
        sid, token = settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
        data = urllib.parse.urlencode({
            "To": phone, "From": settings.TWILIO_FROM,
            "Body": f"Your Velvet Pages code is {code}. It expires in 5 minutes."}).encode()
        req = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data)
        req.add_header("Authorization", "Basic " + base64.b64encode(f"{sid}:{token}".encode()).decode())
        try:
            urllib.request.urlopen(req, timeout=10).read()
        except Exception as exc:  # never log the code
            log.error("OTP SMS delivery failed: %s", type(exc).__name__)
        else:
            cache.set(f"devcode:{phone}", code, settings.OTP_TTL_SECONDS)   # shown on the verify page in dev mode
            print(f"\n[Velvet Pages DEV] One-time code for {phone}: {code}\n", flush=True)


def issue_otp(phone, ip):
    if hit(f"otp-ip:{ip}", 10, 3600) or hit(f"otp-phone:{phone}", settings.OTP_MAX_REQUESTS_PER_HOUR, 3600):
        return False
    code = f"{secrets.randbelow(10 ** 6):06d}"
    OTPCode.objects.filter(phone=phone, used=False).update(used=True)
    OTPCode.objects.create(phone=phone, code_hash=_hash(phone, code))
    _deliver(phone, code)
    return True


def verify_otp(phone, code):
    otp = OTPCode.objects.filter(phone=phone, used=False).order_by("-created_at").first()
    if not otp or otp.created_at < timezone.now() - timedelta(seconds=settings.OTP_TTL_SECONDS):
        return False
    otp.attempts += 1
    if otp.attempts > settings.OTP_MAX_ATTEMPTS:
        otp.used = True
        otp.save()
        return False
    ok = hmac.compare_digest(otp.code_hash, _hash(phone, code))
    if ok:
        otp.used = True
    otp.save()
    return ok
