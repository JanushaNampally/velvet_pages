"""Minimal Google OAuth2 (authorization-code flow) using only the Python standard library."""
import json
import urllib.parse
import urllib.request

from django.conf import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def is_configured():
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def authorize_url(state):
    return AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    })


def get_identity(code):
    """Exchange the code for a token (server-to-server) and read the verified Google profile."""
    data = urllib.parse.urlencode({
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data), timeout=15) as r:
        token = json.load(r)
    req = urllib.request.Request(USERINFO_URL, headers={"Authorization": "Bearer " + token["access_token"]})
    with urllib.request.urlopen(req, timeout=15) as r:
        info = json.load(r)
    return {"sub": str(info["sub"]), "email": (info.get("email") or "").lower(),
            "verified": bool(info.get("email_verified")), "name": info.get("name", "")}