import json

import pytest
from app.routers.websocket import dm_room
from starlette.websockets import WebSocketDisconnect

from app import models
from app.auth import create_access_token, hash_password
from app.routers import websocket as ws_module  
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    monkeypatch.setattr(ws_module, "SessionLocal", TestingSessionLocal)


def make_user(db, name, email):
    """(user_id, token) qaytaradi."""
    user = models.User(
        name=name, email=email, hashed_password=hash_password("123456")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id, create_access_token(user.id)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ─── Ulanish qoidalari ────────────────────────────────────────────────
def test_dm_rejects_invalid_token(client, db):
    vali_id, _ = make_user(db, "Vali", "vali@example.com")
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/dm/{vali_id}?token=yaroqsiz") as ws:
            ws.receive_json()


def test_dm_rejects_self(client, token, test_user):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/dm/{test_user['id']}?token={token}") as ws:
            ws.receive_json()


def test_dm_rejects_unknown_user(client, token):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/dm/9999?token={token}") as ws:
            ws.receive_json()


# ─── Xabar almashish ──────────────────────────────────────────────────
def test_dm_message_reaches_both_users(client, token, test_user, db):
    vali_id, vali_token = make_user(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/dm/{vali_id}?token={token}") as ali:
        assert ali.receive_json()["type"] == "system"

        with client.websocket_connect(
            f"/ws/dm/{test_user['id']}?token={vali_token}"
        ) as vali:
            assert vali.receive_json()["type"] == "system"

            ali.send_text("Salom Vali")

            for ws in (ali, vali):
                msg = ws.receive_json()
                assert msg["type"] == "message"
                assert msg["message"] == "Salom Vali"
                assert msg["username"] == "Ali"
                assert msg["sender_id"] == test_user["id"]


def test_dm_room_same_for_both_directions_unique_per_pair():
    assert dm_room(1, 2) == dm_room(2, 1)   # Ali-Vali va Vali-Ali bir xil xona
    assert dm_room(1, 2) != dm_room(2, 3)   # boshqa juft: boshqa xona
    assert dm_room(1, 2) != dm_room(1, 3)

def test_dm_typing_goes_to_other_only(client, token, test_user, db):
    vali_id, vali_token = make_user(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/dm/{vali_id}?token={token}") as ali, \
         client.websocket_connect(f"/ws/dm/{test_user['id']}?token={vali_token}") as vali:
        ali.receive_json()
        vali.receive_json()

        ali.send_text(json.dumps({"type": "typing"}))
        assert vali.receive_json() == {"type": "typing", "username": "Ali"}

        # Ali o'ziga typing olmaydi va typing bazaga yozilmaydi
        ali.send_text("Salom")
        assert ali.receive_json()["type"] == "message"
        assert vali.receive_json()["type"] == "message"

    data = client.get(f"/ws/dm/{vali_id}/history", headers=auth(token)).json()
    assert [m["content"] for m in data] == ["Salom"]


# ─── Tarix ────────────────────────────────────────────────────────────
def test_dm_messages_saved_and_visible_to_both(client, token, test_user, db):
    vali_id, vali_token = make_user(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/dm/{vali_id}?token={token}") as ali, \
         client.websocket_connect(f"/ws/dm/{test_user['id']}?token={vali_token}") as vali:
        ali.receive_json()
        vali.receive_json()

        ali.send_text("Salom")
        ali.receive_json()
        vali.receive_json()

        vali.send_text("Salom Ali")
        vali.receive_json()
        ali.receive_json()

    # Ali nuqtai nazaridan
    ali_view = client.get(f"/ws/dm/{vali_id}/history", headers=auth(token)).json()
    assert [m["content"] for m in ali_view] == ["Salom", "Salom Ali"]
    assert ali_view[0]["sender_id"] == test_user["id"]
    assert ali_view[0]["receiver_id"] == vali_id
    assert ali_view[1]["sender_id"] == vali_id

    # Vali nuqtai nazaridan: xuddi shu suhbat
    vali_view = client.get(
        f"/ws/dm/{test_user['id']}/history", headers=auth(vali_token)
    ).json()
    assert [m["content"] for m in vali_view] == ["Salom", "Salom Ali"]


def test_dm_history_is_private(client, token, test_user, db):
    vali_id, vali_token = make_user(db, "Vali", "vali@example.com")
    _, guli_token = make_user(db, "Guli", "guli@example.com")

    with client.websocket_connect(f"/ws/dm/{vali_id}?token={token}") as ali, \
         client.websocket_connect(f"/ws/dm/{test_user['id']}?token={vali_token}") as vali:
        ali.receive_json()
        vali.receive_json()
        ali.send_text("Faqat ikkalamiz uchun")
        ali.receive_json()
        vali.receive_json()

    # Guli Vali bilan o'z suhbatini ko'radi: bo'sh
    guli_view = client.get(f"/ws/dm/{vali_id}/history", headers=auth(guli_token))
    assert guli_view.status_code == 200
    assert guli_view.json() == []


def test_dm_history_requires_auth(client, db):
    vali_id, _ = make_user(db, "Vali", "vali@example.com")
    assert client.get(f"/ws/dm/{vali_id}/history").status_code == 401


def test_dm_history_unknown_user_404(authorized_client):
    assert authorized_client.get("/ws/dm/9999/history").status_code == 404


def test_dm_history_with_self_400(authorized_client, test_user):
    response = authorized_client.get(f"/ws/dm/{test_user['id']}/history")
    assert response.status_code == 400


def test_dm_history_last_50_in_order(authorized_client, db, test_user):
    vali_id, _ = make_user(db, "Vali", "vali@example.com")

    db.add_all([
        models.DirectMessage(
            sender_id=test_user["id"] if i % 2 == 0 else vali_id,
            receiver_id=vali_id if i % 2 == 0 else test_user["id"],
            content=f"dm {i}",
        )
        for i in range(60)
    ])
    db.commit()

    data = authorized_client.get(f"/ws/dm/{vali_id}/history").json()
    assert len(data) == 50
    assert data[0]["content"] == "dm 10"    # oxirgi 50 ichida eng eskisi
    assert data[-1]["content"] == "dm 59"   # eng yangisi pastda