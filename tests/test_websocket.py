import json

import pytest
from starlette.websockets import WebSocketDisconnect

from app import models
from app.auth import create_access_token, hash_password
from app.routers import websocket as ws_module
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    # WebSocket token tekshiruvi va xabar saqlash test bazasidan foydalansin
    monkeypatch.setattr(ws_module, "SessionLocal", TestingSessionLocal)


def make_order(authorized_client, foods):
    authorized_client.post("/cart/", json={"food_id": foods[0].id, "quantity": 2})
    return authorized_client.post("/orders/").json()


def make_token(db, name, email):
    user = models.User(
        name=name, email=email, hashed_password=hash_password("123456")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(user.id)


# ─── /ws/orders ───────────────────────────────────────────────────────
def test_ws_connect_with_valid_token(client, token):
    with client.websocket_connect(f"/ws/orders?token={token}") as ws:
        data = ws.receive_json()
        assert data["type"] == "system"


def test_ws_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/orders?token=yaroqsiz") as ws:
            ws.receive_json()


def test_ws_rejects_missing_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/orders") as ws:
            ws.receive_json()


def test_ws_receives_status_update(authorized_client, test_foods, token):
    order = make_order(authorized_client, test_foods)

    with authorized_client.websocket_connect(f"/ws/orders?token={token}") as ws:
        ws.receive_json()  # "Ulandi"

        response = authorized_client.patch(
            f"/orders/{order['id']}/status", json={"status": "confirmed"}
        )
        assert response.status_code == 200

        data = ws.receive_json()
        assert data == {
            "type": "order_status",
            "order_id": order["id"],
            "status": "confirmed",
        }


# ─── Chat ─────────────────────────────────────────────────────────────
def test_chat_rejects_invalid_token(client):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/chat/general?token=yaroqsiz") as ws:
            ws.receive_json()


def test_chat_join_and_message(client, token):
    with client.websocket_connect(f"/ws/chat/general?token={token}") as ws:
        join = ws.receive_json()
        assert join["type"] == "system"
        assert join["users_count"] == 1
        assert "Ali" in join["message"]

        ws.send_text("Salom hammaga")
        msg = ws.receive_json()
        assert msg["type"] == "message"
        assert msg["username"] == "Ali"
        assert msg["message"] == "Salom hammaga"


def test_chat_broadcast_between_users(client, token, db):
    vali_token = make_token(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/chat/general?token={token}") as ali:
        ali.receive_json()  # Ali kirdi

        with client.websocket_connect(f"/ws/chat/general?token={vali_token}") as vali:
            vali.receive_json()  # Vali kirdi
            ali.receive_json()   # Ali "Vali kirdi" ni oladi

            vali.send_text("Salom Ali")
            assert ali.receive_json()["message"] == "Salom Ali"
            assert vali.receive_json()["message"] == "Salom Ali"


def test_chat_rooms_are_separate(client, token, db):
    vali_token = make_token(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/chat/general?token={token}") as ali:
        ali.receive_json()

        with client.websocket_connect(f"/ws/chat/oshxona?token={vali_token}") as vali:
            vali.receive_json()
            vali.send_text("Faqat oshxona uchun")
            assert vali.receive_json()["message"] == "Faqat oshxona uchun"

        # Ali hech narsa olmagan: keyingi xabar faqat o'zining yozgani
        ali.send_text("Men generaldaman")
        assert ali.receive_json()["username"] == "Ali"


# ─── Typing ───────────────────────────────────────────────────────────
def test_chat_typing_event_goes_to_others_only(client, token, db):
    vali_token = make_token(db, "Vali", "vali@example.com")

    with client.websocket_connect(f"/ws/chat/general?token={token}") as ali:
        ali.receive_json()  # Ali kirdi

        with client.websocket_connect(f"/ws/chat/general?token={vali_token}") as vali:
            vali.receive_json()  # Vali kirdi
            ali.receive_json()   # Ali "Vali kirdi" ni oladi

            ali.send_text(json.dumps({"type": "typing"}))

            # Vali "yozmoqda" ni oladi
            event = vali.receive_json()
            assert event == {"type": "typing", "username": "Ali"}

            # Ali o'ziga typing olmaydi: keyingi narsa oddiy xabar bo'lishi kerak
            ali.send_text("Salom")
            assert ali.receive_json()["type"] == "message"
            assert vali.receive_json()["type"] == "message"


def test_chat_typing_is_not_broadcast_as_message(client, token):
    with client.websocket_connect(f"/ws/chat/general?token={token}") as ali:
        ali.receive_json()  # Ali kirdi

        ali.send_text(json.dumps({"type": "typing"}))
        ali.send_text("Oddiy xabar")

        msg = ali.receive_json()
        assert msg["type"] == "message"
        assert msg["message"] == "Oddiy xabar"


# ─── Online users ─────────────────────────────────────────────────────
def test_online_users_empty(client):
    response = client.get("/ws/online")
    assert response.status_code == 200
    assert response.json() == {"online_users": [], "count": 0}


def test_online_users_shows_connected_user(client, token, test_user):
    with client.websocket_connect(f"/ws/orders?token={token}") as ws:
        ws.receive_json()  # "Ulandi"

        data = client.get("/ws/online").json()
        assert data["count"] == 1
        assert test_user["id"] in data["online_users"]

    assert client.get("/ws/online").json()["count"] == 0


# ─── Xabarlar tarixi ──────────────────────────────────────────────────
def test_history_requires_auth(client):
    assert client.get("/ws/rooms/general/history").status_code == 401


def test_history_empty(authorized_client):
    response = authorized_client.get("/ws/rooms/general/history")
    assert response.status_code == 200
    assert response.json() == []


def test_chat_messages_are_saved(authorized_client, token):
    with authorized_client.websocket_connect(f"/ws/chat/general?token={token}") as ws:
        ws.receive_json()  # Ali kirdi
        ws.send_text("Birinchi")
        ws.receive_json()
        ws.send_text("Ikkinchi")
        ws.receive_json()

    data = authorized_client.get("/ws/rooms/general/history").json()
    assert [m["content"] for m in data] == ["Birinchi", "Ikkinchi"]
    assert data[0]["username"] == "Ali"
    assert data[0]["room"] == "general"


def test_typing_and_system_messages_not_saved(authorized_client, token):
    with authorized_client.websocket_connect(f"/ws/chat/general?token={token}") as ws:
        ws.receive_json()  # system
        ws.send_text(json.dumps({"type": "typing"}))
        ws.send_text("Haqiqiy xabar")
        ws.receive_json()

    data = authorized_client.get("/ws/rooms/general/history").json()
    assert [m["content"] for m in data] == ["Haqiqiy xabar"]


def test_history_rooms_are_separate(authorized_client, token):
    with authorized_client.websocket_connect(f"/ws/chat/oshxona?token={token}") as ws:
        ws.receive_json()
        ws.send_text("Faqat oshxona")
        ws.receive_json()

    assert authorized_client.get("/ws/rooms/general/history").json() == []
    assert len(authorized_client.get("/ws/rooms/oshxona/history").json()) == 1


def test_history_returns_last_50_in_order(authorized_client, db, test_user):
    db.add_all([
        models.Message(room="general", user_id=test_user["id"],
                       username="Ali", content=f"xabar {i}")
        for i in range(60)
    ])
    db.commit()

    data = authorized_client.get("/ws/rooms/general/history").json()
    assert len(data) == 50
    assert data[0]["content"] == "xabar 10"    # oxirgi 50 ichida eng eskisi
    assert data[-1]["content"] == "xabar 59"   # eng yangisi pastda