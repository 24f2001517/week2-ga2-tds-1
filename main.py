import os
import time
import uuid
import asyncio
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

ALLOWED_ORIGINS = {
    "https://app-s2twjt.example.com",
}
# Set EXAM_ORIGIN in Render to the origin of the exam/verification page.
exam_origin = os.getenv("EXAM_ORIGIN", "").strip().rstrip("/")
if exam_origin:
    ALLOWED_ORIGINS.add(exam_origin)

EMAIL = os.getenv("EMAIL", "your-logged-in-email@example.com")
RATE_LIMIT = 10
WINDOW_SECONDS = 10.0

# In-memory limiter: suitable for a single Render instance / coding assessment.
_request_times: Dict[str, Deque[float]] = defaultdict(deque)
_rate_lock = asyncio.Lock()


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class ScopedCORSMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        is_allowed = origin in ALLOWED_ORIGINS

        # Browser preflight should be answered without requiring the endpoint.
        if request.method == "OPTIONS" and request.headers.get("access-control-request-method"):
            response = Response(status_code=204)
        else:
            response = await call_next(request)

        if is_allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            requested_headers = request.headers.get("access-control-request-headers")
            response.headers["Access-Control-Allow-Headers"] = (
                requested_headers if requested_headers else
                "Content-Type, X-Request-ID, X-Client-Id"
            )
            response.headers["Access-Control-Max-Age"] = "600"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Apply the limit to API requests; each X-Client-Id has an independent bucket.
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.monotonic()
        async with _rate_lock:
            bucket = _request_times[client_id]
            while bucket and now - bucket[0] >= WINDOW_SECONDS:
                bucket.popleft()
            if len(bucket) >= RATE_LIMIT:
                response = JSONResponse(
                    {"detail": "Rate limit exceeded. Try again later."},
                    status_code=429,
                )
                request_id = getattr(request.state, "request_id", None)
                if request_id:
                    response.headers["X-Request-ID"] = request_id
                return response
            bucket.append(now)

        return await call_next(request)


app = FastAPI(title="Middleware Patterns API", version="1.0.0")

# Starlette wraps middleware in reverse registration order. This ordering ensures
# request context is available to responses from the rate limiter and CORS wraps
# the response so allowed-origin 429 responses also get CORS headers.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(ScopedCORSMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.options("/ping")
async def ping_options():
    return Response(status_code=204)


@app.get("/")
async def root():
    return {"service": "FastAPI middleware service", "health": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}
