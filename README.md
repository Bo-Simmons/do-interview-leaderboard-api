# Global Gaming Leaderboard API

Production-minded FastAPI REST API for global game leaderboards using Redis Sorted Sets.

## Data model and semantics

- Current leaderboard key namespace: `lb:{game_id}`
  - member: `user_id`
  - score: integer
- Namespace is extension-friendly for future scopes (examples):
  - `lb:{game_id}:daily:{YYYYMMDD}`
  - `lb:{game_id}:weekly:{YYYYWW}`
  - `lb:{game_id}:season:{season_id}`
- Rankings are descending by score.
- Tie-breaking follows Redis sorted set member ordering for equal scores.
- All API rank fields are **1-based**.

## Requirements

- Python 3.11+
- Redis 7+

## Local setup

```bash
docker compose up -d redis
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Set Redis URL if needed (default is `redis://localhost:6379/0`):

```bash
export REDIS_URL=redis://localhost:6379/0
```

## Run the API

```bash
uvicorn app.main:app --reload
```

## API endpoints

### 1) Submit score

`POST /v1/games/{game_id}/scores`

Body:

```json
{
  "user_id": "alice",
  "score": 123,
  "mode": "best"
}
```

- `mode="best"` (default): only writes if new score is higher than existing score.
- `mode="latest"`: always overwrite existing score.

Example:

```bash
curl -X POST 'http://127.0.0.1:8000/v1/games/chess/scores' \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":1200,"mode":"best"}'
```

### 2) Leaderboard page

`GET /v1/games/{game_id}/leaderboard?limit=10&offset=0`

- `limit`: only `10` or `100`
- `offset >= 0`

Example:

```bash
curl 'http://127.0.0.1:8000/v1/games/chess/leaderboard?limit=10&offset=0'
```

### 3) User context window

`GET /v1/games/{game_id}/users/{user_id}/context?window=2`

- `window` default `2`, max `25`
- Returns target user plus neighbors above and below.
- If user missing, returns `404 USER_NOT_FOUND`.

Example:

```bash
curl 'http://127.0.0.1:8000/v1/games/chess/users/alice/context?window=2'
```

### 4) Health check

`GET /v1/healthz` -> `200 {"status":"ok"}`

### 5) Readiness check

`GET /v1/readyz` -> pings Redis
- success: `200 {"status":"ok"}`
- failure: `503` with error envelope

## Validation and errors

- `game_id` and `user_id` regex: `^[A-Za-z0-9_-]{1,64}$`
- `score`: integer range `0..2_000_000_000`
- Request validation errors are returned as:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "errors": []
    }
  }
}
```

All errors use:

```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": {}
  }
}
```

## Run tests and lint

```bash
ruff check .
pytest
```

## CI

GitHub Actions workflow in `.github/workflows/ci.yml` runs:
1. `ruff check .`
2. `pytest`

with a Redis service container.
