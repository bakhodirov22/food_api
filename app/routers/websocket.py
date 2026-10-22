import json
from datetime import datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import ALGORITHM, SECRET_KEY, get_current_user
from app.database import SessionLocal, get_db

router = APIRouter(tags=["WebSocket"])


# ─── Buyurtma statusi uchun manager (user_id bo'yicha) ───────────────
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


def get_user_id_from_token(token: str | None) -> int | None:
    """Token to'g'ri va user mavjud bo'lsa user id, aks holda None."""
    user = get_user_from_token(token)
    return user[0] if user else None


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


@router.get("/ws/online")
def online_users():
    user_ids = list(manager.active_connections.keys())
    return {"online_users": user_ids, "count": len(user_ids)}


# ─── Chat (xonalar bo'yicha) ─────────────────────────────────────────
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

    async def broadcast_except(self, room: str, message: dict, exclude: WebSocket):
        for connection in list(self.rooms.get(room, [])):
            if connection is exclude:
                continue
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection, room)


chat_manager = ChatManager()
dm_manager = ChatManager()  # shaxsiy xabarlar: chat xonalaridan alohida


def now() -> str:
    return datetime.now().strftime("%H:%M")


def is_typing_event(text: str) -> bool:
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("type") == "typing"


def save_message(room: str, user_id: int, username: str, content: str):
    # WebSocket'da Depends(get_db) ishlamaydi, shuning uchun o'z sessiyamiz
    db = SessionLocal()
    try:
        db.add(
            models.Message(
                room=room, user_id=user_id, username=username, content=content
            )
        )
        db.commit()
    finally:
        db.close()


@router.websocket("/ws/chat/{room}")
async def chat_ws(websocket: WebSocket, room: str, token: str | None = Query(None)):
    user = get_user_from_token(token)
    if user is None:
        await websocket.close(code=1008)
        return
    user_id, username = user

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

            if is_typing_event(text):
                await chat_manager.broadcast_except(
                    room,
                    {"type": "typing", "username": username},
                    exclude=websocket,
                )
                continue

            save_message(room, user_id, username, text)

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


@router.get("/ws/rooms/{room}/history", response_model=list[schemas.MessageOut])
def room_history(
    room: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    messages = (
        db.query(models.Message)
        .filter(models.Message.room == room)
        .order_by(models.Message.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))  # eskisi tepada, yangisi pastda


# ─── DM: ikki kishi o'rtasida shaxsiy xabar ──────────────────────────
def dm_room(a: int, b: int) -> str:
    """Ali(1)-Vali(2) va Vali(2)-Ali(1) uchun bir xil xona: '1:2'."""
    return f"{min(a, b)}:{max(a, b)}"


def user_exists(user_id: int) -> bool:
    db = SessionLocal()
    try:
        return db.get(models.User, user_id) is not None
    finally:
        db.close()


def save_dm(sender_id: int, receiver_id: int, content: str):
    db = SessionLocal()
    try:
        db.add(
            models.DirectMessage(
                sender_id=sender_id, receiver_id=receiver_id, content=content
            )
        )
        db.commit()
    finally:
        db.close()


@router.websocket("/ws/dm/{target_user_id}")
async def dm_ws(
    websocket: WebSocket,
    target_user_id: int,
    token: str | None = Query(None),
):
    user = get_user_from_token(token)
    if user is None or user[0] == target_user_id or not user_exists(target_user_id):
        await websocket.close(code=1008)  # token xato / o'ziga yozish / user yo'q
        return
    my_id, my_name = user
    room = dm_room(my_id, target_user_id)

    await dm_manager.connect(websocket, room)
    await websocket.send_json({"type": "system", "message": "Ulandi"})

    try:
        while True:
            text = await websocket.receive_text()

            if is_typing_event(text):
                await dm_manager.broadcast_except(
                    room,
                    {"type": "typing", "username": my_name},
                    exclude=websocket,
                )
                continue

            save_dm(my_id, target_user_id, text)

            await dm_manager.broadcast(room, {
                "type": "message",
                "sender_id": my_id,
                "username": my_name,
                "message": text,
                "timestamp": now(),
            })
    except WebSocketDisconnect:
        dm_manager.disconnect(websocket, room)


@router.get("/ws/dm/{target_user_id}/history", response_model=list[schemas.DMOut])
def dm_history(
    target_user_id: int,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if target_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="O'zingizga yozib bo'lmaydi")
    if db.get(models.User, target_user_id) is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    me = current_user.id
    messages = (
        db.query(models.DirectMessage)
        .filter(
            or_(
                and_(
                    models.DirectMessage.sender_id == me,
                    models.DirectMessage.receiver_id == target_user_id,
                ),
                and_(
                    models.DirectMessage.sender_id == target_user_id,
                    models.DirectMessage.receiver_id == me,
                ),
            )
        )
        .order_by(models.DirectMessage.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))  # eskisi tepada, yangisi pastda