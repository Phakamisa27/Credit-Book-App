"""FastAPI application.

One process serves both the JSON API (/api/*) and the frontend, so in daily use
there is a single thing to start and no cross-origin configuration to get
wrong — the same arrangement the Express app had.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from app.api.router import api_router
from app.core.config import FRONTEND_DIR, settings
from app.core.errors import fail, register_exception_handlers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

app = FastAPI(
    title="Credit Book API",
    description="REST API for the Credit Book app — digital credit ledger for a small business owner",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)

register_exception_handlers(app)

# CORS is only needed when the HTML is opened from somewhere other than this
# server (e.g. Live Server on port 5500). Same-origin use never touches it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def guard_and_harden(request: Request, call_next):
    # Signatures and product photos are base64 data URIs, so bodies are large —
    # but not unbounded.
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.json_body_limit_bytes:
                return fail(413, "That upload is too large. Please use a smaller photo.")
        except ValueError:
            pass

    response: Response = await call_next(request)

    # A few sensible headers. Not a full security-header suite — this app runs
    # on the owner's own machine.
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    return response


app.include_router(api_router, prefix="/api")


# ---------------------------------------------------------------- frontend ---
_INDEX = FRONTEND_DIR / "index.html"


def _safe_frontend_path(relative: str) -> Path | None:
    """Resolves a request path inside the frontend directory, or None if it
    escapes it."""
    candidate = (FRONTEND_DIR / relative).resolve()
    try:
        candidate.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        return None
    return candidate


@app.api_route(
    "/{full_path:path}",
    methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
def serve_frontend(full_path: str, request: Request) -> Response:
    """Static frontend, plus the JSON 404 for anything unmatched under /api.

    This catch-all answers every method, not only GET. If it answered GET
    alone, a POST to an unknown /api path would get Starlette's 405 — and
    frontend/js/api.js reads a bodyless 405 as "this is not the Credit Book
    API", which would be a confusing thing to show for a simple typo.
    """
    # Anything under /api that did not match is a 404 in JSON, not the HTML page.
    if full_path == "api" or full_path.startswith("api/"):
        return fail(404, "That endpoint does not exist.")

    # Only a page request can be answered with a page.
    if request.method not in ("GET", "HEAD"):
        return fail(404, "That endpoint does not exist.")

    if full_path:
        candidate = _safe_frontend_path(full_path)
        if candidate is not None:
            if candidate.is_file():
                return FileResponse(candidate)
            # express.static({ extensions: ['html'] }): /login serves login.html
            with_html = candidate.with_name(candidate.name + ".html")
            if with_html.is_file():
                return FileResponse(with_html)

    # Unknown non-API path: hand back the landing page.
    if _INDEX.is_file():
        return FileResponse(_INDEX)
    return fail(404, "That endpoint does not exist.")
