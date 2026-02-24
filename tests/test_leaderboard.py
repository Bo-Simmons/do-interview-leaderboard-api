from __future__ import annotations


def seed_scores(client, game_id: str):
    players = [("alice", 100), ("bob", 150), ("cara", 120)]
    for user_id, score in players:
        resp = client.post(
            f"/v1/games/{game_id}/scores",
            json={"user_id": user_id, "score": score},
        )
        assert resp.status_code == 200


def test_leaderboard_sorted_with_one_based_ranks(client):
    api, _, game_id = client
    seed_scores(api, game_id)

    response = api.get(f"/v1/games/{game_id}/leaderboard", params={"limit": 10, "offset": 0})
    assert response.status_code == 200

    payload = response.json()
    assert [row["user_id"] for row in payload["results"]] == ["bob", "cara", "alice"]
    assert [row["rank"] for row in payload["results"]] == [1, 2, 3]
