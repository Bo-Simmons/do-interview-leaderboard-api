# ARCHITECTURE

## 1) Overview

This service is a small FastAPI application that exposes leaderboard APIs for games. It stores scores in Redis-compatible storage (DigitalOcean Managed Valkey in production) and serves leaderboard reads with low latency using sorted-set operations. The current MVP focuses on one core ranking dimension: a single integer score per `(game_id, user_id)` pair. The API supports score submission, top leaderboard retrieval, and user-relative context (neighbors above and below a player). All public endpoints are versioned under `/v1`, and the live deployment runs on DigitalOcean App Platform with Managed Valkey as the backing store.

Core MVP features:
- Submit or update a score for a user in a game.
- Fetch top leaderboard slices (with constrained `limit` options).
- Fetch a user’s local ranking context (`above`/`below`) with a bounded window.

## 2) API Surface

### `GET /v1/healthz`
Process liveness probe. This only confirms the API process is up and can return a response.

### `GET /v1/readyz`
Dependency readiness probe. This checks Redis connectivity (`PING`) and returns an application error if storage is unavailable.

### `POST /v1/games/{game_id}/scores`
Submits a score for `user_id` in the selected game. Supports `mode=best` (default, keep max score) and `mode=latest` (overwrite with latest submitted value).

### `GET /v1/games/{game_id}/leaderboard?limit=10|100&offset=0`
Returns a leaderboard slice ordered from highest score to lowest score. Ranks are **1-based** in responses; pagination is controlled by zero-based `offset` plus constrained `limit` (`10` or `100`).

### `GET /v1/games/{game_id}/users/{user_id}/context?window=2`
Returns the target user plus up to `window` users above and below them in rank order. Window edges are clipped at top/bottom of leaderboard, so returned `above`/`below` lists may be shorter than requested.

Response semantics to call out explicitly:
- Rank values are always 1-based (even though Redis rank APIs are 0-based internally).
- Leaderboard ordering is descending by score.
- Context window is best-effort within bounds; no padding when neighbors do not exist.

## 3) Storage Design (Why Valkey/Redis ZSET)

Data model:
- Redis key per game: `lb:{game_id}`.
- Sorted-set member: `user_id`.
- Sorted-set score: integer score.

Why ZSET fits this MVP:
- **Update score**: `ZADD` writes are simple and O(log N).
- **Top K**: `ZREVRANGE` directly serves descending leaderboard slices.
- **Rank lookup**: `ZREVRANK` gives user rank efficiently.
- **Neighbors/context**: rank + ranged reads make above/below windows straightforward.

Tie behavior:
- For equal numeric scores, ordering follows Redis sorted-set member ordering semantics (lexicographic member tie-break for equal scores). This is acceptable for MVP but not ideal for strict product-grade fairness requirements.

Alternatives considered (and why not chosen for MVP):
- **Postgres**: Strong relational tooling, but top-K and neighborhood rank reads typically require heavier indexing/query tuning than ZSET for this use case.
- **DynamoDB**: Scales well, but rank-centric queries and neighbor windows are less direct and usually require additional index/materialization patterns.
- **In-memory app state + periodic persistence**: Simplest to prototype, but weak durability and poor multi-instance behavior on App Platform.

## 4) Score Semantics & Consistency

Submission modes:
- `mode=best` (default): update only if incoming score is greater than stored score.
- `mode=latest`: always overwrite with incoming score.

Idempotency expectations:
- Repeating the same payload is effectively idempotent for final stored score.
- The API does **not** implement explicit idempotency keys or dedupe tokens in MVP, so duplicate submissions are still processed as normal writes.

Consistency model:
- Current deployment assumes a single logical Redis endpoint, so reads after writes are typically immediate from that endpoint.
- If moved to replicated or geo-distributed topologies, stale reads and failover timing could affect immediate rank visibility; MVP does not add versioning/vector-clock style protections.

## 5) Validation & Error Handling

Validation constraints in the API layer:
- `game_id`, `user_id`: regex `^[A-Za-z0-9_-]{1,64}$`.
- `score`: integer, bounded `0..2_000_000_000`.
- `limit`: only `10` or `100`.
- `offset`: `>= 0`.
- `window`: `0..25`.

Standard error envelope:
```json
{
  "error": {
    "code": "...",
    "message": "...",
    "details": { }
  }
}
```

Notable error codes used by this MVP:
- `VALIDATION_ERROR` (400): request payload/query/path contract violations.
- `USER_NOT_FOUND` (404): requested user has no score for that game.
- `REDIS_UNAVAILABLE` (503): readiness check failed against Redis.

## 6) Operational Considerations

Health vs readiness:
- `healthz` proves process liveness.
- `readyz` proves dependency readiness (Redis connectivity).

Both exist because orchestration platforms need to distinguish “process is alive” from “instance is safe to receive traffic.”

Configuration:
- `REDIS_URL` controls backing store connection.
- `PORT` is honored in App Platform runtime command for correct container binding.
- `.python-version` pins Python `3.12` to align buildpack/runtime expectations.

Observability today:
- Basic FastAPI/Uvicorn logging and test coverage.

What should be added for production:
- Structured logs with request correlation IDs.
- Endpoint-level latency/error metrics (Prometheus/OpenTelemetry).
- Dashboards and alerting on error rates, p95 latency, and Redis health.

## 7) Testing Strategy

Current tests focus on API and service semantics:
- Score update semantics (`best` ignores lower scores; `latest` overwrites).
- Leaderboard ordering and 1-based ranks.
- User context behavior, including top/bottom edge handling.
- Not-found behavior for missing user context.

Gaps (not covered by current test suite):
- Load/performance testing.
- Chaos/failure testing (Redis failover, network partitions).
- Multi-region replication consistency behavior.
- Security-focused tests (abuse/rate-limit evasion, authn/authz).

## 8) CI / Automation

Current GitHub Actions pipeline:
- Triggers on push and pull request.
- Starts Redis service container.
- Installs dependencies.
- Runs Ruff lint checks.
- Runs pytest suite.

What to add for production-grade automation:
- Build artifact/image creation and signing.
- SAST and dependency vulnerability scanning.
- Release workflow with version tags and changelog automation.
- Optional deployment gates based on staged environment checks.

## 9) Limitations (Intentional MVP Constraints)

Accepted constraints for interview scope:
- No authentication/authorization.
- No per-client quotas or rate limiting.
- No explicit multi-tenant isolation model beyond `game_id` key partitioning.
- No retention windows, seasonality resets, or archival strategy.
- No user profile metadata (display names, country, device, etc.).
- Limited pagination shape (`limit` only 10 or 100).
- No strong idempotency guarantees via request keys.
- No anti-cheat/abuse controls.

These choices keep complexity low and make behavior easy to reason about during interview evaluation.

## 10) Scaling & Future Improvements

Concrete next steps:
- **Seasonal/daily key strategy**: use keys like `lb:{game_id}:{season_id}` (or daily/weekly suffixes) to support resets and historical snapshots without destructive rewrites.
- **Sharding / cluster strategy**: partition by `game_id` hash slot (Redis Cluster or app-level routing) so high-volume games can scale horizontally.
- **Caching + richer pagination**: add cursor-based pagination and optional response caching for heavy read paths to reduce repeated range scans.
- **Idempotency keys**: store short-lived request IDs to dedupe retries and make client retries safer.
- **Write-ahead event stream**: publish score-change events (Redis Streams/Kafka) for analytics, audit trails, and downstream materializations.
- **Abuse prevention**: add per-IP/user/game rate limits and anomaly detection hooks to reduce scripted score spam.
- **Stronger deterministic tie-breaks**: encode composite scoring (e.g., score + timestamp nonce) or maintain side metadata for strict ordering guarantees.
- **Persistence/backup/DR**: define snapshot/restore policy, cross-zone backups, and tested recovery runbooks.

## 11) What I’d Change for a Real Product

If this moved beyond interview MVP, priorities would be:
- Authn/authz and API key or OAuth-based caller identity.
- Quotas and monetization-aligned usage controls.
- Formal SLOs (availability, latency) with error budgets.
- Observability stack with dashboards, tracing, and alerting.
- Schema evolution/versioning strategy for API and event contracts.
- Planned data migrations and backfill workflows.
- Multi-region architecture with clear consistency and failover policy.
