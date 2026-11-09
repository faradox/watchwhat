"""Who is asking, by AUTH_MODE (config.py). Only /api/private/ uses this.

- "proxy": a reverse proxy login (for example nginx + Authelia) sets
  Remote-User plus a shared proxy secret; the name must be in ALLOWED_USERS.
- "basic": HTTP Basic auth checked here against BASIC_PASSWORD.
- "none": everyone is the first household member.

The public pages ask GET /api/private/me whether someone is logged in. That
answer must never carry a Basic challenge, or every visitor would get a
browser login dialog; only GET /api/private/login asks for the password.
After that, browsers send the login with every request under /api/private/.
"""

import base64
import binascii
import hmac
from urllib.parse import urlsplit

from fastapi import HTTPException, Request, status

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def current_user(request: Request) -> str:
    """The login name, or 401/403. Writes must also come from our own pages."""
    user = _user(request, challenge=False)
    if request.method in UNSAFE_METHODS:
        _require_same_origin(request)
    return user


async def login_user(request: Request) -> str:
    """Like current_user, but asks for Basic auth (only GET /api/private/login)."""
    return _user(request, challenge=True)


def _user(request: Request, challenge: bool) -> str:
    settings = request.app.state.settings
    if settings.auth_mode == "none":
        return settings.household[0]
    if settings.auth_mode == "basic":
        return _basic_user(request, settings, challenge)
    return _proxy_user(request, settings)


def _proxy_user(request: Request, settings) -> str:
    """As vouched for by the reverse proxy (for example nginx + Authelia)."""
    if not settings.proxy_secret:
        # Only reachable in development: Settings.validate() refuses production
        # without it. Without a header, you are the first household member.
        fallback = settings.allowed_users[0] if settings.allowed_users else "dev"
        return request.headers.get("remote-user") or fallback
    sent = request.headers.get("x-proxy-secret", "")
    if not hmac.compare_digest(sent.encode(), settings.proxy_secret.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not via the proxy")
    user = request.headers.get("remote-user", "")
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not logged in")
    if user not in settings.allowed_users:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed")
    return user


def _basic_user(request: Request, settings, challenge: bool) -> str:
    headers = (
        {"WWW-Authenticate": 'Basic realm="watchwhat", charset="UTF-8"'} if challenge else None
    )
    denied = HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required", headers=headers)
    scheme, _, encoded = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "basic" or not encoded:
        raise denied
    try:
        decoded = base64.b64decode(encoded.strip(), validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        raise denied from None
    user, sep, password = decoded.partition(":")
    password_ok = hmac.compare_digest(password.encode(), settings.basic_password.encode())
    if not sep or not user or not password_ok or user not in settings.allowed_users:
        raise denied
    return user


def _require_same_origin(request: Request) -> None:
    """A cookie or cached Basic login alone must not allow writes from other sites."""
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-site request")
    origin = request.headers.get("origin")
    if origin:
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        if urlsplit(origin).netloc != host:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cross-site request")
