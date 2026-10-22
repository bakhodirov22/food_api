from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6, max_length=72)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: str | None = None

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RestaurantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=255)


class RestaurantOut(BaseModel):
    id: int
    name: str
    address: str | None = None

    model_config = {"from_attributes": True}


class FoodCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)
    restaurant_id: int


class FoodUpdate(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)
    restaurant_id: int | None = None


class FoodOut(BaseModel):
    id: int
    name: str
    price: float
    restaurant_id: int

    model_config = {"from_attributes": True}


class CartAdd(BaseModel):
    food_id: int
    quantity: int = Field(default=1, ge=1)


class CartItemOut(BaseModel):
    id: int
    food: FoodOut
    quantity: int
    subtotal: float


class CartOut(BaseModel):
    items: list[CartItemOut]
    total_price: float


class OrderStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    delivered = "delivered"
    cancelled = "cancelled"


class OrderItemOut(BaseModel):
    food_id: int
    food_name: str | None = None
    quantity: int
    price: float
    subtotal: float


class OrderOut(BaseModel):
    id: int
    status: str
    total_price: float
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class MessageOut(BaseModel):
    id: int
    room: str
    username: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DMOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}