from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/cart", tags=["Cart"])


def build_cart(user: models.User, db: Session) -> schemas.CartOut:
    cart_items = (
        db.query(models.CartItem)
        .filter(models.CartItem.user_id == user.id)
        .all()
    )

    items = []
    total = 0
    for item in cart_items:
        subtotal = item.food.price * item.quantity
        total += subtotal
        items.append(
            schemas.CartItemOut(
                id=item.id,
                food=schemas.FoodOut.model_validate(item.food),
                quantity=item.quantity,
                subtotal=subtotal,
            )
        )

    return schemas.CartOut(items=items, total_price=total)


@router.post("/", response_model=schemas.CartOut, status_code=201)
def add_to_cart(
    data: schemas.CartAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    food = db.get(models.Food, data.food_id)
    if food is None:
        raise HTTPException(status_code=404, detail="Food topilmadi")

    cart_item = (
        db.query(models.CartItem)
        .filter(
            models.CartItem.user_id == current_user.id,
            models.CartItem.food_id == data.food_id,
        )
        .first()
    )

    if cart_item:
        cart_item.quantity += data.quantity
    else:
        cart_item = models.CartItem(
            user_id=current_user.id,
            food_id=data.food_id,
            quantity=data.quantity,
        )
        db.add(cart_item)

    db.commit()
    return build_cart(current_user, db)


@router.get("/", response_model=schemas.CartOut)
def view_cart(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return build_cart(current_user, db)