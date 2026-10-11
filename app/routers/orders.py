from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/orders", tags=["Orders"])


def order_to_out(order: models.Order) -> schemas.OrderOut:
    items = [
        schemas.OrderItemOut(
            food_id=item.food_id,
            food_name=item.food.name if item.food else None,
            quantity=item.quantity,
            price=item.price,
            subtotal=item.price * item.quantity,
        )
        for item in order.items
    ]
    return schemas.OrderOut(
        id=order.id,
        status=order.status,
        total_price=order.total_price,
        created_at=order.created_at,
        items=items,
    )


def get_own_order(order_id: int, user: models.User, db: Session) -> models.Order:
    order = db.get(models.Order, order_id)
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order topilmadi")
    return order


@router.post("/", response_model=schemas.OrderOut, status_code=201)
def create_order(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    cart_items = (
        db.query(models.CartItem)
        .filter(models.CartItem.user_id == current_user.id)
        .all()
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="Savat bo'sh")

    # Savatdagi barcha foodlar hali mavjudligini tekshiramiz
    for item in cart_items:
        if item.food is None:
            raise HTTPException(
                status_code=400,
                detail="Savatdagi food endi mavjud emas, savatni yangilang",
            )

    order = models.Order(user_id=current_user.id, total_price=0)
    db.add(order)
    db.flush()  # order.id ni olish uchun

    total = 0
    for item in cart_items:
        db.add(
            models.OrderItem(
                order_id=order.id,
                food_id=item.food_id,
                quantity=item.quantity,
                price=item.food.price,
            )
        )
        total += item.food.price * item.quantity
        db.delete(item)  # savatdan olib tashlaymiz

    order.total_price = total
    db.commit()
    db.refresh(order)
    return order_to_out(order)


@router.get("/", response_model=list[schemas.OrderOut])
def my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    orders = (
        db.query(models.Order)
        .filter(models.Order.user_id == current_user.id)
        .order_by(models.Order.id.desc())
        .all()
    )
    return [order_to_out(o) for o in orders]


@router.get("/{order_id}", response_model=schemas.OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return order_to_out(get_own_order(order_id, current_user, db))


@router.patch("/{order_id}/status", response_model=schemas.OrderOut)
def change_status(
    order_id: int,
    data: schemas.OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    order = get_own_order(order_id, current_user, db)
    order.status = data.status.value
    db.commit()
    db.refresh(order)
    return order_to_out(order)