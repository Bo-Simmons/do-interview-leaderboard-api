"""Redis client creation helpers used by application startup."""

from __future__ import annotations

import os

from redis.asyncio import Redis

DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", DEFAULT_REDIS_URL)


def create_redis_client(redis_url: str | None = None) -> Redis:
    return Redis.from_url(redis_url or get_redis_url(), decode_responses=True)
