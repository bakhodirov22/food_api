from fastapi import FastAPI

from app import models
from app.database import engine
from app.routers import auth, cart, foods, orders, restaurants, websocket

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Food Delivery API")

app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(foods.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(websocket.router)


@app.get("/")
def home():
    return {"message": "Food API ishlayapti!"}