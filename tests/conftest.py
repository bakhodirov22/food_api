import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.main import app

# Test bazasi: xotirada, fayl yaratmaydi
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def test_user(client):
    data = {"name": "Ali", "email": "ali@example.com", "password": "123456"}
    response = client.post("/auth/register", json=data)
    assert response.status_code == 201
    user = response.json()
    user["password"] = data["password"]
    return user


@pytest.fixture()
def token(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture()
def authorized_client(client, token):
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def test_restaurant(db):
    restaurant = models.Restaurant(name="Oqtepa Lavash", address="Toshkent")
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant


@pytest.fixture()
def test_foods(db, test_restaurant):
    foods = [
        models.Food(name="Burger", price=30000, restaurant_id=test_restaurant.id),
        models.Food(name="Pizza", price=50000, restaurant_id=test_restaurant.id),
    ]
    db.add_all(foods)
    db.commit()
    for f in foods:
        db.refresh(f)
    return foods

@pytest.fixture(autouse=True)
def no_real_emails(monkeypatch):
    monkeypatch.setattr("app.routers.auth.send_welcome_email", lambda **kw: None)
    monkeypatch.setattr("app.routers.orders.send_order_notification", lambda **kw: None)