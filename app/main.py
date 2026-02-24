from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import APIError
from app.api.routes import router
from app.models.schemas import ErrorBody, ErrorResponse
from app.services.leaderboard import LeaderboardService
from app.storage.redis import create_redis_client


def create_app() -> FastAPI:
    app = FastAPI(title="Leaderboard API", version="1.0.0")

    redis_client = create_redis_client()
    app.state.redis = redis_client
    app.state.leaderboard_service = LeaderboardService(redis_client)

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

    @app.on_event("shutdown")
    async def close_redis() -> None:
        await app.state.redis.aclose()

    app.include_router(router)
    return app


app = create_app()
