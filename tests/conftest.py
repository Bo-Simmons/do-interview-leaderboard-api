from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from redis import Redis

from app.main import create_app


@pytest.fixture(scope="session")
def redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture()
def client(redis_url: str):
    app = create_app()
    sync_redis = Redis.from_url(redis_url, decode_responses=True)

    game_id = f"testgame_{uuid.uuid4().hex}"

    with TestClient(app) as test_client:
        yield test_client, sync_redis, game_id

    for key in sync_redis.scan_iter(match=f"lb:{game_id}*"):
        sync_redis.delete(key)
