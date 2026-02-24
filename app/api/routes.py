"""HTTP route handlers for leaderboard operations and service health checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request

from app.api.errors import APIError
from app.models.schemas import (
    IDENTIFIER_PATTERN,
    HealthResponse,
    LeaderboardResponse,
    LeaderboardRow,
    ReadyResponse,
    ScoreResult,
    ScoreSubmission,
    UserContext,
    UserContextResponse,
)
from app.services.leaderboard import LeaderboardService, UserNotFoundError

router = APIRouter(prefix="/v1")


def get_service(request: Request) -> LeaderboardService:
    return request.app.state.leaderboard_service


@router.post("/games/{game_id}/scores", response_model=ScoreResult)
async def submit_score(
    payload: ScoreSubmission,
    game_id: str = Path(pattern=IDENTIFIER_PATTERN),
    service: LeaderboardService = Depends(get_service),
) -> ScoreResult:
    ranked = await service.submit_score(
        game_id=game_id,
        user_id=payload.user_id,
        score=payload.score,
        mode=payload.mode,
    )
    return ScoreResult(
        game_id=game_id,
        user_id=ranked.user_id,
        score=ranked.score,
        rank=ranked.rank,
    )


@router.get("/games/{game_id}/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    game_id: str = Path(pattern=IDENTIFIER_PATTERN),
    limit: int = Query(default=10),
    offset: int = Query(default=0, ge=0),
    service: LeaderboardService = Depends(get_service),
) -> LeaderboardResponse:
    if limit not in {10, 100}:
        raise APIError(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            status_code=400,
            details={
                "errors": [
                    {"loc": ["query", "limit"], "msg": "limit must be 10 or 100"}
                ]
            },
        )

    rows = await service.get_leaderboard(game_id, limit, offset)
    return LeaderboardResponse(
        game_id=game_id,
        limit=limit,
        offset=offset,
        results=[LeaderboardRow(rank=r.rank, user_id=r.user_id, score=r.score) for r in rows],
    )


@router.get("/games/{game_id}/users/{user_id}/context", response_model=UserContextResponse)
async def get_user_context(
    game_id: str = Path(pattern=IDENTIFIER_PATTERN),
    user_id: str = Path(pattern=IDENTIFIER_PATTERN),
    window: int = Query(default=2, ge=0, le=25),
    service: LeaderboardService = Depends(get_service),
) -> UserContextResponse:
    try:
        context = await service.get_user_context(game_id, user_id, window)
    except UserNotFoundError as exc:
        raise APIError(
            code="USER_NOT_FOUND",
            message="User has no score for this game",
            status_code=404,
        ) from exc

    return UserContextResponse(
        user=UserContext(
            rank=context.user.rank,
            user_id=context.user.user_id,
            score=context.user.score,
        ),
        above=[UserContext(rank=r.rank, user_id=r.user_id, score=r.score) for r in context.above],
        below=[UserContext(rank=r.rank, user_id=r.user_id, score=r.score) for r in context.below],
    )


# These probes are intended for infrastructure and do not need to appear in API docs.
@router.get("/healthz", response_model=HealthResponse, include_in_schema=False)
async def healthz() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=ReadyResponse, include_in_schema=False)
async def readyz(service: LeaderboardService = Depends(get_service)) -> ReadyResponse:
    try:
        # Readiness verifies backing Redis connectivity, not just process liveness.
        is_ready = await service.ping()
    except Exception as exc:
        raise APIError(
            code="REDIS_UNAVAILABLE",
            message="Redis readiness check failed",
            status_code=503,
        ) from exc

    if not is_ready:
        raise APIError(
            code="REDIS_UNAVAILABLE",
            message="Redis readiness check failed",
            status_code=503,
        )
    return ReadyResponse(status="ok")
