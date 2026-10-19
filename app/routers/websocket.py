import json
from datetime import datetime

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

class ChatManager:
    def __init__(self):
        # {room: [websocket, ...]}
        self.rooms: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room: str):
        await websocket.accept()
        self.rooms.setdefault(room, []).append(websocket)

    def disconnect(self, websocket: WebSocket, room: str):
        connections = self.rooms.get(room, [])
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self.rooms.pop(room, None)

    def count(self, room: str) -> int:
        return len(self.rooms.get(room, []))

    async def broadcast(self, room: str, message: dict):
        for connection in list(self.rooms.get(room, [])):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection, room)


chat_manager = ChatManager()


def get_user_from_token(token: str | None):
    """Token to'g'ri bo'lsa (id, name), aks holda None."""
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
        return (user.id, user.name) if user else None
    finally:
        db.close()


def now() -> str:
    return datetime.now().strftime("%H:%M")


@router.websocket("/ws/chat/{room}")
async def chat_ws(websocket: WebSocket, room: str, token: str | None = Query(None)):
    user = get_user_from_token(token)
    if user is None:
        await websocket.close(code=1008)
        return
    _, username = user

    await chat_manager.connect(websocket, room)
    await chat_manager.broadcast(room, {
        "type": "system",
        "message": f"{username} xonaga kirdi",
        "users_count": chat_manager.count(room),
        "timestamp": now(),
    })

    try:
        while True:
            text = await websocket.receive_text()
            await chat_manager.broadcast(room, {
                "type": "message",
                "username": username,
                "message": text,
                "timestamp": now(),
            })
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, room)
        await chat_manager.broadcast(room, {
            "type": "system",
            "message": f"{username} xonadan chiqdi",
            "users_count": chat_manager.count(room),
            "timestamp": now(),
        })


@router.get("/ws/rooms")
def active_rooms():
    return {"rooms": {r: len(c) for r, c in chat_manager.rooms.items()}}

