import pytest
from starlette.websockets import WebSocketDisconnect

from app.routers import websocket as ws_module
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def use_test_db(monkeypatch):
    # WebSocket token tekshiruvi test bazasidan foydalansin
    monkeypatch.setattr(ws_module, "SessionLocal", TestingSessionLocal)


def make_order(authorized_client, foods):
    authorized_client.post("/cart/", json={"food_id": foods[0].id, "quantity": 2})
    return authorized_client.post("/orders/").json()


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

def make_token(db, name, email):
    from app import models
    from app.auth import create_access_token, hash_password

    user = models.User(
        name=name, email=email, hashed_password=hash_password("123456")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(user.id)


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
        ali.send_text("Men general'dаman")
        assert ali.receive_json()["username"] == "Ali"