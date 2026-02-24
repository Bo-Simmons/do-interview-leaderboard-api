"""FastAPI application wiring for routes, error handlers, and lifespan."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import APIError
from app.api.routes import router
from app.models.schemas import ErrorBody, ErrorResponse
from app.services.leaderboard import LeaderboardService
from app.storage.redis import create_redis_client


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    redis_client = create_redis_client()
    app.state.redis = redis_client
    app.state.leaderboard_service = LeaderboardService(redis_client)
    try:
        yield
    finally:
        await redis_client.aclose()


def create_app() -> FastAPI:
    app = FastAPI(title="Leaderboard API", version="1.0.0", lifespan=app_lifespan)

    @app.exception_handler(APIError)
    async def api_error_handler(_: Request, exc: APIError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorBody(code=exc.code, message=exc.message, details=exc.details),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        payload = ErrorResponse(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": exc.errors()},
            ),
        )
        return JSONResponse(status_code=400, content=payload.model_dump(exclude_none=True))

    app.include_router(router)
    return app


app = create_app()
