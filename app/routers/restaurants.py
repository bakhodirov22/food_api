import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.cache import cache_delete_pattern, cache_get, cache_set
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])

LIST_KEY = "restaurants:all"
LIST_TTL = 300  # 5 daqiqa


@router.post("/", response_model=schemas.RestaurantOut, status_code=201)
def create_restaurant(
    data: schemas.RestaurantCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = models.Restaurant(name=data.name, address=data.address)
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    cache_delete_pattern("restaurants:*")
    return restaurant


@router.get("/", response_model=list[schemas.RestaurantOut])
def list_restaurants(db: Session = Depends(get_db)):
    cached = cache_get(LIST_KEY)
    if cached is not None:  # bo'sh ro'yxat ham hit hisoblanadi
        logger.info(f"Cache HIT: {LIST_KEY}")
        return cached

    logger.info(f"Cache MISS: {LIST_KEY}")
    data = [
        schemas.RestaurantOut.model_validate(r).model_dump()
        for r in db.query(models.Restaurant).all()
    ]
    cache_set(LIST_KEY, data, ttl=LIST_TTL)
    return data