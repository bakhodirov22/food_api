import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models
from app.cache import redis_ok
from app.database import engine
from app.routers import auth, cart, foods, orders, restaurants, websocket, upload

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

os.makedirs("uploads", exist_ok=True)  # mount dan OLDIN yaratilishi shart


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Server ishga tushganda Redis ni tekshirish
    if redis_ok():
        logger.info("✅ Redis ulandi")
    else:
        logger.warning("⚠️ Redis ulanmadi: cache ishlamaydi, lekin API ishlaydi")
    yield


app = FastAPI(title="Food Delivery API", lifespan=lifespan)

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


@app.get("/health")
def health():
    return {"status": "ok", "redis": "ok" if redis_ok() else "error"}