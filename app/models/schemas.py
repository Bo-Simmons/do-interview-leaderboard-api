"""Pydantic request/response schemas for the public leaderboard API.

These models define input validation and response contracts used by routes
and exception handlers.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

IDENTIFIER_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
Identifier = Annotated[str, StringConstraints(pattern=IDENTIFIER_PATTERN)]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class ScoreSubmission(BaseModel):
    user_id: Identifier
    score: int = Field(ge=0, le=2_000_000_000)
    mode: Literal["best", "latest"] = "best"


class ScoreResult(BaseModel):
    game_id: Identifier
    user_id: Identifier
    score: int
    rank: int


class LeaderboardRow(BaseModel):
    rank: int
    user_id: Identifier
    score: int


class LeaderboardResponse(BaseModel):
    game_id: Identifier
    limit: Literal[10, 100]
    offset: int = Field(ge=0)
    results: list[LeaderboardRow]


class UserContext(BaseModel):
    rank: int
    user_id: Identifier
    score: int


class UserContextResponse(BaseModel):
    user: UserContext
    above: list[UserContext]
    below: list[UserContext]


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ok"]
