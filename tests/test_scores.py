from __future__ import annotations


def post_score(client, game_id: str, user_id: str, score: int, mode: str = "best"):
    return client.post(
        f"/v1/games/{game_id}/scores",
        json={"user_id": user_id, "score": score, "mode": mode},
    )


def test_best_mode_ignores_lower_score(client):
    api, _, game_id = client

    first = post_score(api, game_id, "alice", 100, "best")
    second = post_score(api, game_id, "alice", 90, "best")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["score"] == 100


def test_best_mode_updates_higher_score(client):
    api, _, game_id = client

    post_score(api, game_id, "alice", 100, "best")
    higher = post_score(api, game_id, "alice", 120, "best")

    assert higher.status_code == 200
    assert higher.json()["score"] == 120


def test_latest_mode_overwrites(client):
    api, _, game_id = client

    post_score(api, game_id, "alice", 100, "best")
    latest = post_score(api, game_id, "alice", 80, "latest")

    assert latest.status_code == 200
    assert latest.json()["score"] == 80
