def test_add_to_cart(authorized_client, test_foods):
    burger = test_foods[0]
    response = authorized_client.post(
        "/cart/", json={"food_id": burger.id, "quantity": 2}
    )
    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["subtotal"] == 60000
    assert data["total_price"] == 60000


def test_add_to_cart_default_quantity(authorized_client, test_foods):
    response = authorized_client.post("/cart/", json={"food_id": test_foods[0].id})
    assert response.status_code == 201
    assert response.json()["items"][0]["quantity"] == 1


def test_add_same_food_increases_quantity(authorized_client, test_foods):
    burger = test_foods[0]
    authorized_client.post("/cart/", json={"food_id": burger.id, "quantity": 2})
    response = authorized_client.post(
        "/cart/", json={"food_id": burger.id, "quantity": 1}
    )
    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 1  # yangi qator ochilmagan
    assert data["items"][0]["quantity"] == 3
    assert data["total_price"] == 90000


def test_add_food_not_found(authorized_client):
    response = authorized_client.post("/cart/", json={"food_id": 99999})
    assert response.status_code == 404


def test_add_invalid_quantity(authorized_client, test_foods):
    response = authorized_client.post(
        "/cart/", json={"food_id": test_foods[0].id, "quantity": 0}
    )
    assert response.status_code == 422


def test_add_to_cart_without_token(client, test_foods):
    response = client.post("/cart/", json={"food_id": test_foods[0].id})
    assert response.status_code == 401


def test_view_cart_empty(authorized_client):
    response = authorized_client.get("/cart/")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total_price": 0}


def test_view_cart_total(authorized_client, test_foods):
    burger, pizza = test_foods
    authorized_client.post("/cart/", json={"food_id": burger.id, "quantity": 2})
    authorized_client.post("/cart/", json={"food_id": pizza.id, "quantity": 1})

    response = authorized_client.get("/cart/")
    assert response.status_code == 200

    data = response.json()
    assert len(data["items"]) == 2
    assert data["total_price"] == 110000  # 30000*2 + 50000*1


def test_view_cart_without_token(client):
    response = client.get("/cart/")
    assert response.status_code == 401


def test_cart_is_per_user(client, authorized_client, test_foods, db):
    from app import models
    from app.auth import hash_password, create_access_token

    authorized_client.post("/cart/", json={"food_id": test_foods[0].id})

    other = models.User(
        name="Vali", email="vali@example.com", hashed_password=hash_password("123456")
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    response = client.get(
        "/cart/", headers={"Authorization": f"Bearer {create_access_token(other.id)}"}
    )
    assert response.status_code == 200
    assert response.json()["items"] == []  # Valining savati bo'sh