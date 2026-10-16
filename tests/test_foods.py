from app import models


def test_create_food(authorized_client, test_restaurant):
    response = authorized_client.post(
        "/foods/",
        json={"name": "Burger", "price": 30000, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Burger"
    assert data["price"] == 30000
    assert data["restaurant_id"] == test_restaurant.id


def test_create_food_without_token(client, test_restaurant):
    response = client.post(
        "/foods/",
        json={"name": "Burger", "price": 30000, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 401


def test_create_food_restaurant_not_found(authorized_client):
    response = authorized_client.post(
        "/foods/",
        json={"name": "Burger", "price": 30000, "restaurant_id": 99999},
    )
    assert response.status_code == 404


def test_create_food_invalid_price(authorized_client, test_restaurant):
    response = authorized_client.post(
        "/foods/",
        json={"name": "Burger", "price": 0, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 422


def test_list_foods(client, test_foods):
    response = client.get("/foods/")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_foods_filter_by_restaurant(client, db, test_foods, test_restaurant):
    other = models.Restaurant(name="Evos", address="Toshkent")
    db.add(other)
    db.commit()
    db.refresh(other)
    db.add(models.Food(name="Lavash", price=35000, restaurant_id=other.id))
    db.commit()

    response = client.get(f"/foods/?restaurant_id={test_restaurant.id}")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 2
    assert all(f["restaurant_id"] == test_restaurant.id for f in data)

    response = client.get(f"/foods/?restaurant_id={other.id}")
    assert len(response.json()) == 1


def test_get_food(client, test_foods):
    response = client.get(f"/foods/{test_foods[0].id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Burger"


def test_get_food_not_found(client):
    response = client.get("/foods/99999")
    assert response.status_code == 404


def test_update_food(authorized_client, test_foods):
    response = authorized_client.put(
        f"/foods/{test_foods[0].id}", json={"price": 32000}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["price"] == 32000
    assert data["name"] == "Burger"  # nom o'zgarmagan


def test_update_food_without_token(client, test_foods):
    response = client.put(f"/foods/{test_foods[0].id}", json={"price": 32000})
    assert response.status_code == 401


def test_update_food_not_found(authorized_client):
    response = authorized_client.put("/foods/99999", json={"price": 32000})
    assert response.status_code == 404


def test_delete_food(authorized_client, test_foods):
    response = authorized_client.delete(f"/foods/{test_foods[0].id}")
    assert response.status_code == 204

    response = authorized_client.get(f"/foods/{test_foods[0].id}")
    assert response.status_code == 404


def test_delete_food_without_token(client, test_foods):
    response = client.delete(f"/foods/{test_foods[0].id}")
    assert response.status_code == 401


def test_delete_food_not_found(authorized_client):
    response = authorized_client.delete("/foods/99999")
    assert response.status_code == 404

def test_update_food_restaurant_not_found(authorized_client, test_foods):
    response = authorized_client.put(
        f"/foods/{test_foods[0].id}", json={"restaurant_id": 99999}
    )
    assert response.status_code == 404

def test_create_food_empty_name(authorized_client, test_restaurant):
    response = authorized_client.post(
        "/foods/",
        json={"name": "", "price": 30000, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 422


def test_create_food_long_name(authorized_client, test_restaurant):
    response = authorized_client.post(
        "/foods/",
        json={"name": "A" * 1000, "price": 30000, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 422


def test_create_food_negative_price(authorized_client, test_restaurant):
    response = authorized_client.post(
        "/foods/",
        json={"name": "Burger", "price": -5, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 422