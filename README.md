# Global Gaming Leaderboard API

Production-minded FastAPI service for global game leaderboards backed by Redis Sorted Sets.

## Live Deployment (DigitalOcean)

- Live base URL: `https://do-interview-leaderboard-api-4ns9n.ondigitalocean.app`
- All API endpoints are served under the `/v1` prefix.
- Interactive API docs are available at: https://do-interview-leaderboard-api-4ns9n.ondigitalocean.app/docs
- Backing store: DigitalOcean Managed Valkey (Redis-compatible), with the app deployed on DigitalOcean App Platform.

## API Endpoints

- `GET /v1/healthz`
- `GET /v1/readyz`
- `POST /v1/games/{game_id}/scores`
- `GET /v1/games/{game_id}/leaderboard?limit=10|100&offset=0`
- `GET /v1/games/{game_id}/users/{user_id}/context?window=2`

## Quickstart

### Option A: Docker available

```bash
docker compose up -d redis
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option B: No Docker (common in dev containers)

```bash
sudo apt-get update
sudo apt-get install -y redis-server redis-tools
redis-server --daemonize yes
redis-cli ping   # expect: PONG
export REDIS_URL=redis://localhost:6379/0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Deployment Notes

- App Platform run command must honor `PORT` (for example: `uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}`), so the container binds the platform-assigned port in production.
- Python version is pinned via root-level `.python-version` to `3.12` for App Platform buildpack/runtime compatibility (including binary wheels/toolchain expectations during install).
- `REDIS_URL` is provided as an App Platform environment variable and points at the attached DigitalOcean Managed Valkey cluster.

## Run tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"   # or: pip install -e .
export REDIS_URL=redis://localhost:6379/0
ruff check .
pytest -q
```

## API Examples (curl)

> Examples below use local development URL `http://127.0.0.1:8000` and `jq` for readability; you can omit `| jq` if not installed.

### Submit a score (default `mode=best`)

```bash
curl -sS -X POST 'http://127.0.0.1:8000/v1/games/chess/scores' \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":1200}' | jq
```

### `best` mode ignores a lower score

```bash
# First write a high score
curl -sS -X POST 'http://127.0.0.1:8000/v1/games/chess/scores' \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":1200,"mode":"best"}' | jq

# Try to write a lower score; stored score remains 1200
curl -sS -X POST 'http://127.0.0.1:8000/v1/games/chess/scores' \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":900,"mode":"best"}' | jq
```

### Fetch leaderboard top 10

```bash
curl -sS 'http://127.0.0.1:8000/v1/games/chess/leaderboard?limit=10&offset=0' | jq
```

### Fetch user context (`window=1`)

```bash
curl -sS 'http://127.0.0.1:8000/v1/games/chess/users/alice/context?window=1' | jq
```

## Live API Examples (curl)

> These examples use `jq` for readability; `jq` is optional.

```bash
export BASE="https://do-interview-leaderboard-api-4ns9n.ondigitalocean.app"
```

### Health and readiness

```bash
curl -sS "$BASE/v1/healthz" | jq
curl -sS "$BASE/v1/readyz" | jq
```

### Submit three scores

```bash
curl -sS -X POST "$BASE/v1/games/chess/scores" \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":1200}' | jq

curl -sS -X POST "$BASE/v1/games/chess/scores" \
  -H 'content-type: application/json' \
  -d '{"user_id":"bob","score":1100}' | jq

curl -sS -X POST "$BASE/v1/games/chess/scores" \
  -H 'content-type: application/json' \
  -d '{"user_id":"carol","score":1300}' | jq
```

### `best` mode ignores a lower score

```bash
# First set a high score
curl -sS -X POST "$BASE/v1/games/chess/scores" \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":1500,"mode":"best"}' | jq

# Lower score is ignored; alice remains at 1500
curl -sS -X POST "$BASE/v1/games/chess/scores" \
  -H 'content-type: application/json' \
  -d '{"user_id":"alice","score":900,"mode":"best"}' | jq
```

### Get top 10 leaderboard

```bash
curl -sS "$BASE/v1/games/chess/leaderboard?limit=10&offset=0" | jq
```

### Get user context (`window=1`)

```bash
curl -sS "$BASE/v1/games/chess/users/alice/context?window=1" | jq
```

## Design & Semantics

- Redis Sorted Set per game: key `lb:{game_id}`, member `user_id`, integer score.
- `mode=best` updates only when incoming score is higher.
- `mode=latest` always overwrites with the newest score.
- Response ranks are **1-based**.
- Equal-score tie-breaking follows Redis member ordering.
- Validation constraints:
  - `user_id` and `game_id`: `^[A-Za-z0-9_-]{1,64}$`
  - `score`: integer in `0..2_000_000_000`
  - leaderboard `limit`: only `10` or `100`
