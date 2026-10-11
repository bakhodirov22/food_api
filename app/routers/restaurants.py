from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


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
    return restaurant


@router.get("/", response_model=list[schemas.RestaurantOut])
def list_restaurants(db: Session = Depends(get_db)):
    return db.query(models.Restaurant).all()