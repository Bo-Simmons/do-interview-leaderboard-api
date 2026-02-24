"""Core leaderboard operations backed by Redis sorted sets."""

from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis


@dataclass(slots=True)
class RankedUser:
    rank: int
    user_id: str
    score: int


@dataclass(slots=True)
class UserContextResult:
    user: RankedUser
    above: list[RankedUser]
    below: list[RankedUser]


class UserNotFoundError(Exception):
    """Raised when a user has no score for a game."""


def leaderboard_key(game_id: str) -> str:
    return f"lb:{game_id}"


class LeaderboardService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    async def submit_score(
        self,
        game_id: str,
        user_id: str,
        score: int,
        mode: str = "best",
    ) -> RankedUser:
        key = leaderboard_key(game_id)

        if mode == "latest":
            await self.redis.zadd(key, {user_id: score})
        else:
            current = await self.redis.zscore(key, user_id)
            if current is None or score > int(current):
                await self.redis.zadd(key, {user_id: score})

        rank = await self.redis.zrevrank(key, user_id)
        applied_score = await self.redis.zscore(key, user_id)
        if rank is None or applied_score is None:
            raise RuntimeError("Score write/read inconsistency")
        # Redis returns zero-based rank; API contract is one-based.
        return RankedUser(rank=rank + 1, user_id=user_id, score=int(applied_score))

    async def get_leaderboard(self, game_id: str, limit: int, offset: int) -> list[RankedUser]:
        key = leaderboard_key(game_id)
        end = offset + limit - 1
        rows = await self.redis.zrevrange(key, offset, end, withscores=True)
        results: list[RankedUser] = []
        for index, (user_id, score) in enumerate(rows, start=offset + 1):
            results.append(RankedUser(rank=index, user_id=user_id, score=int(score)))
        return results

    async def get_user_context(self, game_id: str, user_id: str, window: int) -> UserContextResult:
        key = leaderboard_key(game_id)

        rank = await self.redis.zrevrank(key, user_id)
        user_score = await self.redis.zscore(key, user_id)
        if rank is None or user_score is None:
            raise UserNotFoundError(user_id)

        above_start = max(rank - window, 0)
        above_end = rank - 1
        above_rows = []
        if above_end >= above_start:
            above_rows = await self.redis.zrevrange(key, above_start, above_end, withscores=True)

        below_start = rank + 1
        below_end = rank + window
        below_rows = await self.redis.zrevrange(key, below_start, below_end, withscores=True)

        above = [
            RankedUser(rank=above_start + idx + 1, user_id=row_user_id, score=int(row_score))
            for idx, (row_user_id, row_score) in enumerate(above_rows)
        ]
        below = [
            RankedUser(rank=below_start + idx + 1, user_id=row_user_id, score=int(row_score))
            for idx, (row_user_id, row_score) in enumerate(below_rows)
        ]

        return UserContextResult(
            user=RankedUser(rank=rank + 1, user_id=user_id, score=int(user_score)),
            above=above,
            below=below,
        )

    async def ping(self) -> bool:
        response = await self.redis.ping()
        return bool(response)
