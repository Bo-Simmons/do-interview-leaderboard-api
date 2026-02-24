from __future__ import annotations


def seed_context_scores(client, game_id: str):
    players = [
        ("alice", 300),
        ("bob", 250),
        ("cara", 200),
        ("dan", 150),
        ("emma", 100),
    ]
    for user_id, score in players:
        resp = client.post(f"/v1/games/{game_id}/scores", json={"user_id": user_id, "score": score})
        assert resp.status_code == 200


def test_context_returns_correct_above_and_below(client):
    api, _, game_id = client
    seed_context_scores(api, game_id)

    response = api.get(f"/v1/games/{game_id}/users/cara/context", params={"window": 2})
    assert response.status_code == 200
    body = response.json()

    assert body["user"] == {"rank": 3, "user_id": "cara", "score": 200}
    assert [u["user_id"] for u in body["above"]] == ["alice", "bob"]
    assert [u["rank"] for u in body["above"]] == [1, 2]
    assert [u["user_id"] for u in body["below"]] == ["dan", "emma"]
    assert [u["rank"] for u in body["below"]] == [4, 5]


def test_context_handles_top_and_bottom(client):
    api, _, game_id = client
    seed_context_scores(api, game_id)

    top = api.get(f"/v1/games/{game_id}/users/alice/context", params={"window": 2})
    assert top.status_code == 200
    top_body = top.json()
    assert top_body["above"] == []
    assert [u["user_id"] for u in top_body["below"]] == ["bob", "cara"]

    bottom = api.get(f"/v1/games/{game_id}/users/emma/context", params={"window": 2})
    assert bottom.status_code == 200
    bottom_body = bottom.json()
    assert [u["user_id"] for u in bottom_body["above"]] == ["cara", "dan"]
    assert bottom_body["below"] == []


def test_context_returns_404_when_user_not_found(client):
    api, _, game_id = client
    seed_context_scores(api, game_id)

    response = api.get(f"/v1/games/{game_id}/users/zoe/context")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
