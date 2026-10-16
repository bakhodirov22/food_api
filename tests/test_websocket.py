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