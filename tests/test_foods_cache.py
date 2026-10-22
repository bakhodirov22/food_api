import redis

from app import models


class BrokenRedis:
    """Har qanday chaqiruvda ulanish xatosini beradi."""

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise redis.ConnectionError("Redis o'chiq")
        return fail


def test_list_foods_is_cached_after_first_request(client, test_foods, fake_redis):
    assert fake_redis.exists("foods:all") == 0

    response = client.get("/foods/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    assert fake_redis.exists("foods:all") == 1
    assert 0 < fake_redis.ttl("foods:all") <= 300


def test_list_foods_second_request_served_from_cache(client, db, test_foods):
    first = client.get("/foods/").json()
    assert {f["name"] for f in first} == {"Burger", "Pizza"}

    # Bazani API'ni aylanib o'tib o'zgartiramiz
    food = db.get(models.Food, test_foods[0].id)
    food.name = "O'zgargan"
    db.commit()

    # Javob keshdan keladi, shuning uchun eski nom qoladi
    second = client.get("/foods/").json()
    assert {f["name"] for f in second} == {"Burger", "Pizza"}


def test_list_foods_filter_uses_separate_key(
    client, test_foods, test_restaurant, fake_redis
):
    key = f"foods:restaurant:{test_restaurant.id}"

    response = client.get(f"/foods/?restaurant_id={test_restaurant.id}")
    assert len(response.json()) == 2

    assert fake_redis.exists(key) == 1
    assert fake_redis.exists("foods:all") == 0


def test_empty_list_is_cached(client, db, test_restaurant):
    assert client.get("/foods/").json() == []

    db.add(models.Food(name="Lavash", price=25000, restaurant_id=test_restaurant.id))
    db.commit()

    # Bo'sh ro'yxat ham hit: yangi taom hali ko'rinmaydi
    assert client.get("/foods/").json() == []


def test_get_food_is_cached(client, db, test_foods, fake_redis):
    food_id = test_foods[0].id

    assert client.get(f"/foods/{food_id}").json()["name"] == "Burger"
    assert fake_redis.exists(f"foods:{food_id}") == 1

    food = db.get(models.Food, food_id)
    food.name = "Boshqa"
    db.commit()

    assert client.get(f"/foods/{food_id}").json()["name"] == "Burger"


def test_get_food_404_is_not_cached(client, fake_redis):
    assert client.get("/foods/9999").status_code == 404
    assert fake_redis.keys("foods:*") == []


def test_create_food_clears_cache(
    authorized_client, test_foods, test_restaurant, fake_redis
):
    assert len(authorized_client.get("/foods/").json()) == 2
    assert fake_redis.exists("foods:all") == 1

    response = authorized_client.post(
        "/foods/",
        json={"name": "Lavash", "price": 25000, "restaurant_id": test_restaurant.id},
    )
    assert response.status_code == 201
    assert fake_redis.exists("foods:all") == 0

    assert len(authorized_client.get("/foods/").json()) == 3


def test_update_food_clears_cache(authorized_client, test_foods, fake_redis):
    food_id = test_foods[0].id
    authorized_client.get(f"/foods/{food_id}")
    authorized_client.get("/foods/")
    assert fake_redis.exists(f"foods:{food_id}") == 1
    assert fake_redis.exists("foods:all") == 1

    response = authorized_client.put(f"/foods/{food_id}", json={"name": "Yangi burger"})
    assert response.status_code == 200
    assert fake_redis.keys("foods:*") == []

    assert authorized_client.get(f"/foods/{food_id}").json()["name"] == "Yangi burger"
    names = {f["name"] for f in authorized_client.get("/foods/").json()}
    assert "Yangi burger" in names


def test_delete_food_clears_cache(authorized_client, test_foods, fake_redis):
    food_id = test_foods[0].id
    authorized_client.get(f"/foods/{food_id}")
    assert fake_redis.exists(f"foods:{food_id}") == 1

    assert authorized_client.delete(f"/foods/{food_id}").status_code == 204
    assert fake_redis.keys("foods:*") == []

    assert authorized_client.get(f"/foods/{food_id}").status_code == 404


def test_foods_work_when_redis_is_down(
    authorized_client, test_foods, test_restaurant, monkeypatch
):
    monkeypatch.setattr("app.cache.redis_client", BrokenRedis())

    response = authorized_client.get("/foods/")
    assert response.status_code == 200
    assert len(response.json()) == 2

    assert authorized_client.get(f"/foods/{test_foods[0].id}").status_code == 200

    created = authorized_client.post(
        "/foods/",
        json={"name": "Lavash", "price": 25000, "restaurant_id": test_restaurant.id},
    )
    assert created.status_code == 201