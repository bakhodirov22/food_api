from app import models
from app.auth import create_access_token, hash_password


def fill_cart(client, foods):
    """Burger x 2 + Pizza x 1 savatga qo'shadi."""
    burger, pizza = foods
    client.post("/cart/", json={"food_id": burger.id, "quantity": 2})
    client.post("/cart/", json={"food_id": pizza.id, "quantity": 1})


def test_create_order(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)

    response = authorized_client.post("/orders/")
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "pending"
    assert data["total_price"] == 110000  # 30000*2 + 50000*1
    assert len(data["items"]) == 2

    by_name = {i["food_name"]: i for i in data["items"]}
    assert by_name["Burger"]["quantity"] == 2
    assert by_name["Burger"]["subtotal"] == 60000
    assert by_name["Pizza"]["quantity"] == 1
    assert by_name["Pizza"]["subtotal"] == 50000


def test_create_order_clears_cart(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)
    authorized_client.post("/orders/")

    response = authorized_client.get("/cart/")
    assert response.json() == {"items": [], "total_price": 0}


def test_create_order_empty_cart(authorized_client):
    response = authorized_client.post("/orders/")
    assert response.status_code == 400


def test_create_order_without_token(client):
    response = client.post("/orders/")
    assert response.status_code == 401


def test_order_keeps_price_after_food_price_change(
    authorized_client, test_foods, db
):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    # Food narxi keyin o'zgaradi
    test_foods[0].price = 99999
    db.commit()

    response = authorized_client.get(f"/orders/{order['id']}")
    assert response.status_code == 200
    assert response.json()["total_price"] == 110000  # eski narx saqlangan


def test_list_my_orders(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)
    authorized_client.post("/orders/")
    fill_cart(authorized_client, test_foods)
    authorized_client.post("/orders/")

    response = authorized_client.get("/orders/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_orders_without_token(client):
    response = client.get("/orders/")
    assert response.status_code == 401


def test_get_order(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    response = authorized_client.get(f"/orders/{order['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == order["id"]


def test_get_order_not_found(authorized_client):
    response = authorized_client.get("/orders/99999")
    assert response.status_code == 404


def test_cannot_see_other_user_order(authorized_client, client, test_foods, db):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    other = models.User(
        name="Vali", email="vali@example.com", hashed_password=hash_password("123456")
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}

    # Vali Alining orderini ko'ra olmaydi
    assert client.get(f"/orders/{order['id']}", headers=headers).status_code == 404
    # Va ro'yxatida ham yo'q
    assert client.get("/orders/", headers=headers).json() == []


def test_change_status(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    response = authorized_client.patch(
        f"/orders/{order['id']}/status", json={"status": "confirmed"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


def test_change_status_invalid_value(authorized_client, test_foods):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    response = authorized_client.patch(
        f"/orders/{order['id']}/status", json={"status": "abc"}
    )
    assert response.status_code == 422


def test_change_status_other_user_order(authorized_client, client, test_foods, db):
    fill_cart(authorized_client, test_foods)
    order = authorized_client.post("/orders/").json()

    other = models.User(
        name="Vali", email="vali@example.com", hashed_password=hash_password("123456")
    )
    db.add(other)
    db.commit()
    db.refresh(other)
    headers = {"Authorization": f"Bearer {create_access_token(other.id)}"}

    response = client.patch(
        f"/orders/{order['id']}/status", json={"status": "cancelled"}, headers=headers
    )
    assert response.status_code == 404