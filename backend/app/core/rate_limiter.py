from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.observability import log_structured_event, metrics_collector


@dataclass(slots=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_in_seconds: int


class SlidingWindowRateLimiter:
    """
    Implementa un Rate Limiter exacto por ventana deslizante de 60 segundos:
    Máximo 10 requests/minuto por usuario (Requisito Funcional Estricto).
    """

    def __init__(self, max_requests_per_minute: int = 10, window_seconds: int = 60) -> None:
        self.max_requests = max_requests_per_minute
        self.window_seconds = window_seconds
        self._user_buckets: dict[str, deque[float]] = {}

    def check_and_consume(self, user_id: str) -> RateLimitResult:
        now = time.monotonic()
        bucket = self._user_buckets.setdefault(user_id, deque())

        # Purgar timestamps fuera de la ventana de 60 segundos
        cutoff = now - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window_seconds - (now - bucket[0])))
            metrics_collector.rate_limited_requests += 1
            log_structured_event(
                "RATE_LIMIT_EXCEEDED",
                f"Usuario {user_id} alcanzó el límite de {self.max_requests} req/min",
                severity="WARNING",
                user_id=user_id,
                retry_after_seconds=retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Límite superado: máximo {self.max_requests} consultas por minuto por usuario.",
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                },
            )

        bucket.append(now)
        remaining = max(0, self.max_requests - len(bucket))
        reset_in = int(self.window_seconds - (now - bucket[0])) if bucket else self.window_seconds
        return RateLimitResult(
            allowed=True,
            limit=self.max_requests,
            remaining=remaining,
            reset_in_seconds=reset_in,
        )

    def reset_all(self) -> None:
        self._user_buckets.clear()


user_rate_limiter = SlidingWindowRateLimiter(
    max_requests_per_minute=settings.rate_limit_requests_per_minute,
    window_seconds=60,
)
