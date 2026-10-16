import jwt
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app import models
from app.auth import ALGORITHM, SECRET_KEY
from app.database import SessionLocal

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    def __init__(self):
        # {user_id: [websocket1, websocket2, ...]}
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        connections = self.active_connections.get(user_id, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        for connection in list(self.active_connections.get(user_id, [])):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection, user_id)


manager = ConnectionManager()


def get_user_id_from_token(token: str | None) -> int | None:
    """Token to'g'ri va user mavjud bo'lsa user id, aks holda None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None

    db = SessionLocal()
    try:
        user = db.get(models.User, user_id)
        return user.id if user else None
    finally:
        db.close()


@router.websocket("/ws/orders")
async def orders_ws(websocket: WebSocket, token: str | None = Query(None)):
    user_id = get_user_id_from_token(token)
    if user_id is None:
        await websocket.close(code=1008)  # policy violation
        return

    await manager.connect(websocket, user_id)
    await websocket.send_json({"type": "system", "message": "Ulandi"})

    try:
        while True:
            await websocket.receive_text()  # ulanishni tirik ushlab turadi
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)