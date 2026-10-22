import redis

from app import models


class BrokenRedis:
    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise redis.ConnectionError("Redis o'chiq")
        return fail


def test_restaurants_list_is_cached(client, test_restaurant, fake_redis):
    response = client.get("/restaurants/")
    assert response.status_code == 200
    assert [r["name"] for r in response.json()] == ["Oqtepa Lavash"]
    assert fake_redis.exists("restaurants:all") == 1


def test_restaurants_second_request_served_from_cache(client, db, test_restaurant):
    client.get("/restaurants/")

    restaurant = db.get(models.Restaurant, test_restaurant.id)
    restaurant.name = "Boshqa nom"
    db.commit()

    assert client.get("/restaurants/").json()[0]["name"] == "Oqtepa Lavash"


def test_empty_restaurants_list_is_cached(client, db):
    assert client.get("/restaurants/").json() == []

    db.add(models.Restaurant(name="Yangi", address=None))
    db.commit()

    assert client.get("/restaurants/").json() == []


def test_create_restaurant_clears_cache(authorized_client, test_restaurant, fake_redis):
    authorized_client.get("/restaurants/")
    assert fake_redis.exists("restaurants:all") == 1

    response = authorized_client.post(
        "/restaurants/", json={"name": "Yangi", "address": "Samarqand"}
    )
    assert response.status_code == 201
    assert fake_redis.exists("restaurants:all") == 0

    assert len(authorized_client.get("/restaurants/").json()) == 2


def test_restaurants_work_when_redis_is_down(client, test_restaurant, monkeypatch):
    monkeypatch.setattr("app.cache.redis_client", BrokenRedis())

    response = client.get("/restaurants/")
    assert response.status_code == 200
    assert len(response.json()) == 1