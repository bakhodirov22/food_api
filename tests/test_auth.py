import jwt

from app.auth import ALGORITHM, SECRET_KEY


def test_register(client):
    response = client.post(
        "/auth/register",
        json={"name": "Vali", "email": "vali@example.com", "password": "123456"},
    )
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "vali@example.com"
    assert data["name"] == "Vali"
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client, test_user):
    response = client.post(
        "/auth/register",
        json={"name": "Boshqa", "email": test_user["email"], "password": "123456"},
    )
    assert response.status_code == 400


def test_register_short_password(client):
    response = client.post(
        "/auth/register",
        json={"name": "Vali", "email": "vali@example.com", "password": "123"},
    )
    assert response.status_code == 422


def test_login(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_token_valid(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["email"], "password": test_user["password"]},
    )
    token = response.json()["access_token"]

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == str(test_user["id"])


def test_login_wrong_password(client, test_user):
    response = client.post(
        "/auth/login",
        data={"username": test_user["email"], "password": "noto'g'ri"},
    )
    assert response.status_code == 401


def test_login_wrong_email(client):
    response = client.post(
        "/auth/login",
        data={"username": "yoq@example.com", "password": "123456"},
    )
    assert response.status_code == 401


def test_me(authorized_client, test_user):
    response = authorized_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == test_user["email"]


def test_me_without_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_invalid_token(client):
    response = client.get("/auth/me", headers={"Authorization": "Bearer yaroqsiz"})
    assert response.status_code == 401