from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    cart_items = relationship("CartItem", back_populates="user")
    orders = relationship("Order", back_populates="user")


class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)

    foods = relationship("Food", back_populates="restaurant")


class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)

    restaurant = relationship("Restaurant", back_populates="foods")


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)

    user = relationship("User", back_populates="cart_items")
    food = relationship("Food")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_price = Column(Float, default=0, nullable=False)
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)  # buyurtma vaqtidagi narx

    order = relationship("Order", back_populates="items")
    food = relationship("Food")