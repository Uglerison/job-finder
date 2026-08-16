"""Loopback-origin and double-submit CSRF protection for the local web app."""

from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

router = APIRouter(prefix="/api", tags=["security"])
CSRF_COOKIE = "job_finder_csrf"
CSRF_HEADER = "x-csrf-token"
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@router.get("/security/csrf")
def issue_csrf_token(request: Request) -> JSONResponse:
    """Issue a short-lived browser token without persisting credentials."""

    token = secrets.token_urlsafe(32)
    response = JSONResponse({"token": token})
    response.set_cookie(
        CSRF_COOKIE,
        token,
        httponly=False,
        samesite="strict",
        secure=request.url.scheme == "https",
        path="/",
    )
    return response


class LocalSecurityMiddleware(BaseHTTPMiddleware):
    """Reject cross-origin mutations and browser mutations without CSRF proof."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.method in MUTATING_METHODS:
            origin = request.headers.get("origin")
            if origin is not None:
                if not _is_loopback_origin(request, origin):
                    return JSONResponse(
                        {"detail": "Origem não permitida para esta operação local."},
                        status_code=403,
                    )
                cookie_token = request.cookies.get(CSRF_COOKIE)
                header_token = request.headers.get(CSRF_HEADER)
                if (
                    cookie_token is None
                    or header_token is None
                    or not secrets.compare_digest(cookie_token, header_token)
                ):
                    return JSONResponse(
                        {"detail": "Token CSRF ausente ou inválido."},
                        status_code=403,
                    )
        return await call_next(request)


def _is_loopback_origin(request: Request, origin: str) -> bool:
    parsed = urlsplit(origin)
    request_host = request.headers.get("host", "")
    expected = f"{request.url.scheme}://{request_host}"
    if origin.rstrip("/") == expected.rstrip("/"):
        return True
    return parsed.hostname in {"127.0.0.1", "localhost"} and parsed.port == request.url.port
