from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/foods", tags=["Foods"])


@router.post("/", response_model=schemas.FoodOut, status_code=201)
def create_food(
    data: schemas.FoodCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    restaurant = db.get(models.Restaurant, data.restaurant_id)
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restoran topilmadi")

    food = models.Food(
        name=data.name,
        price=data.price,
        restaurant_id=data.restaurant_id,
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food


@router.get("/", response_model=list[schemas.FoodOut])
def list_foods(
    restaurant_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Food)
    if restaurant_id is not None:
        query = query.filter(models.Food.restaurant_id == restaurant_id)
    return query.all()


@router.get("/{food_id}", response_model=schemas.FoodOut)
def get_food(food_id: int, db: Session = Depends(get_db)):
    food = db.get(models.Food, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food topilmadi")
    return food


@router.put("/{food_id}", response_model=schemas.FoodOut)
def update_food(
    food_id: int,
    data: schemas.FoodUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    food = db.get(models.Food, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food topilmadi")

    changes = data.model_dump(exclude_unset=True)

    if "restaurant_id" in changes:
        if db.get(models.Restaurant, changes["restaurant_id"]) is None:
            raise HTTPException(status_code=404, detail="Restoran topilmadi")

    for field, value in changes.items():
        setattr(food, field, value)

    db.commit()
    db.refresh(food)
    return food


@router.delete("/{food_id}", status_code=204)
def delete_food(
    food_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    food = db.get(models.Food, food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food topilmadi")

    db.delete(food)
    db.commit()