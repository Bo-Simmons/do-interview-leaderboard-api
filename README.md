# Global Gaming Leaderboard API

Production-minded FastAPI service for global game leaderboards backed by Redis Sorted Sets.

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

## DigitalOcean App Platform deployment note

DigitalOcean App Platform buildpack detection relies on a root-level `requirements.txt`, so this repository includes one for deployment detection and runtime installs.

For local development, you can still use the existing `pyproject.toml` workflow (for example, `pip install -e ".[dev]"`) exactly as before.

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

> Examples below use `jq` for readability; you can omit `| jq` if not installed.

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
