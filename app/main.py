import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models
from app.database import engine
from app.routers import auth, cart, foods, orders, restaurants, websocket, upload

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

models.Base.metadata.create_all(bind=engine)

os.makedirs("uploads", exist_ok=True)  # mount dan OLDIN yaratilishi shart

app = FastAPI(title="Food Delivery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # faqat dars uchun; productionda aniq domen yozing
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(foods.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(websocket.router)
app.include_router(upload.router)


@app.get("/")
def home():
    return {"message": "Food API ishlayapti!"}