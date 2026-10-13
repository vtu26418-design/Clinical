"""Simple in-memory rate limiter for API endpoints."""
from __future__ import annotations

import time
import ipaddress
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter partitioned by client IP and route category."""

    def __init__(
        self,
        app,
        default_limit: int = 60,
        training_limit: int = 10,
        assistant_limit: int = 30,
        window_seconds: float = 60.0,
        trusted_proxy_hosts: str = '',
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.training_limit = training_limit
        self.assistant_limit = assistant_limit
        self.window_seconds = window_seconds
        self.trusted_proxies = []
        for host in trusted_proxy_hosts.split(','):
            if host.strip():
                self.trusted_proxies.append(ipaddress.ip_network(host.strip(), strict=False))

        # State storage: bucket_key -> {"tokens": float, "last_updated": float}
        self._buckets: dict[str, dict[str, float]] = defaultdict(
            lambda: {"tokens": float(self.default_limit), "last_updated": time.time()}
        )

    def _get_client_ip(self, request: Request) -> str:
        peer = request.client.host if request.client else 'unknown'
        def trusted(value):
            try:
                address = ipaddress.ip_address(value)
                return any(address in network for network in self.trusted_proxies)
            except ValueError:
                return False
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for and trusted(peer):
            # Walk from the socket toward the user. A trusted proxy must append
            # its real peer, so an attacker-supplied leftmost value is ignored.
            hops = [value.strip() for value in forwarded_for.split(',')]
            if len(hops) > 20:
                return peer
            for value in reversed(hops):
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    return peer
                if not trusted(value):
                    return value
            return hops[0] if hops else peer
        return peer

    def _resolve_limit_and_category(self, path: str, method: str) -> tuple[int, str]:
        path_lower = path.lower()
        # Training endpoints
        if (
            "experiment" in path_lower
            or "/train" in path_lower
            or path_lower.startswith("/api/v1/experiments")
            or path_lower.startswith("/api/v1/phase-experiments")
        ) and method in {"POST", "PUT"}:
            return self.training_limit, "training"

        # AI assistant endpoints
        if (
            path_lower.startswith("/api/v1/assistant")
            or path_lower.startswith("/api/v5/conversations")
            or "/assistant" in path_lower
            or "/chat" in path_lower
        ):
            return self.assistant_limit, "assistant"

        return self.default_limit, "default"

    async def dispatch(self, request: Request, call_next):
        # Exempt CORS preflight requests
        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not path.startswith('/api/'):
            return await call_next(request)
        # Allow internal static files or health check without strict limiting
        if path == "/api/v1/health":
            response = await call_next(request)
            response.headers["X-RateLimit-Remaining"] = str(self.default_limit)
            return response

        limit, category = self._resolve_limit_and_category(path, request.method)
        ip = self._get_client_ip(request)
        bucket_key = f"{ip}:{category}"

        now = time.time()
        # Limit memory use under long-running services with changing clients.
        if len(self._buckets) >= 10000 and bucket_key not in self._buckets:
            stale = [key for key, value in self._buckets.items()
                     if now - value['last_updated'] > self.window_seconds * 2]
            for key in stale:
                del self._buckets[key]
            if len(self._buckets) >= 10000:
                return JSONResponse(status_code=429, content={'detail': 'Too many requests. Rate limit exceeded.'},
                                    headers={'Retry-After': '60', 'X-RateLimit-Remaining': '0'})
        bucket = self._buckets[bucket_key]

        # Token regeneration based on elapsed time
        elapsed = now - bucket["last_updated"]
        fill_rate = limit / self.window_seconds
        bucket["tokens"] = min(float(limit), bucket["tokens"] + (elapsed * fill_rate))
        bucket["last_updated"] = now

        if bucket["tokens"] < 1.0:
            retry_after = int(max(1.0, (1.0 - bucket["tokens"]) / fill_rate)) if fill_rate > 0 else 60
            response = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit exceeded."},
                headers={
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(retry_after),
                },
            )
            return response

        # Consume 1 token
        bucket["tokens"] -= 1.0
        remaining = int(max(0.0, bucket["tokens"]))

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
