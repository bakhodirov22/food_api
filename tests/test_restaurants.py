def test_create_restaurant(authorized_client):
    response = authorized_client.post(
        "/restaurants/",
        json={"name": "Evos", "address": "Toshkent, Yunusobod"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Evos"
    assert data["address"] == "Toshkent, Yunusobod"
    assert "id" in data


def test_create_restaurant_without_token(client):
    response = client.post("/restaurants/", json={"name": "Evos"})
    assert response.status_code == 401


def test_create_restaurant_without_name(authorized_client):
    response = authorized_client.post("/restaurants/", json={"address": "Toshkent"})
    assert response.status_code == 422


def test_list_restaurants(client, test_restaurant):
    response = client.get("/restaurants/")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == test_restaurant.name


def test_list_restaurants_empty(client):
    response = client.get("/restaurants/")
    assert response.status_code == 200
    assert response.json() == []