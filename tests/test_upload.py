import pytest

from app.routers import upload as upload_module


@pytest.fixture(autouse=True)
def temp_upload_dir(monkeypatch, tmp_path):
    monkeypatch.setattr(upload_module, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


def png(name="rasm.png"):
    return {"file": (name, b"fake-png-bytes", "image/png")}


# ─── /upload/image ────────────────────────────────────────────────────
def test_upload_requires_auth(client):
    response = client.post("/upload/image", files=png())
    assert response.status_code == 401


def test_upload_image_success(authorized_client, temp_upload_dir):
    response = authorized_client.post("/upload/image", files=png())
    assert response.status_code == 200

    data = response.json()
    assert data["filename"].endswith(".png")
    assert data["url"] == f"/uploads/{data['filename']}"
    assert data["size"] == len(b"fake-png-bytes")
    assert data["content_type"] == "image/png"
    assert (temp_upload_dir / data["filename"]).exists()


def test_upload_rejects_wrong_type(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("matn.txt", b"salom", "text/plain")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []


def test_upload_rejects_too_large(authorized_client, monkeypatch, temp_upload_dir):
    monkeypatch.setattr(upload_module, "MAX_SIZE", 10)
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("katta.png", b"x" * 20, "image/png")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []


def test_upload_without_file_returns_422(authorized_client):
    response = authorized_client.post("/upload/image")
    assert response.status_code == 422


def test_upload_extension_comes_from_content_type(authorized_client):
    # Fayl nomida nuqta yo'q, baribir to'g'ri kengaytma chiqadi
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("rasm", b"data", "image/jpeg")},
    )
    assert response.status_code == 200
    assert response.json()["filename"].endswith(".jpg")


# ─── /upload/images ───────────────────────────────────────────────────
def test_upload_multiple_success(authorized_client, temp_upload_dir):
    files = [
        ("files", ("a.png", b"aaa", "image/png")),
        ("files", ("b.jpg", b"bbb", "image/jpeg")),
    ]
    response = authorized_client.post("/upload/images", files=files)
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert len(list(temp_upload_dir.iterdir())) == 2


def test_upload_multiple_skips_invalid_types(authorized_client):
    files = [
        ("files", ("a.png", b"aaa", "image/png")),
        ("files", ("b.txt", b"bbb", "text/plain")),
    ]
    response = authorized_client.post("/upload/images", files=files)
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_upload_multiple_max_five(authorized_client):
    files = [("files", (f"{i}.png", b"x", "image/png")) for i in range(6)]
    response = authorized_client.post("/upload/images", files=files)
    assert response.status_code == 400


# ─── /upload/avatar ───────────────────────────────────────────────────
def test_avatar_requires_auth(client):
    response = client.post("/upload/avatar", files=png())
    assert response.status_code == 401


def test_avatar_success_and_visible_in_me(authorized_client, temp_upload_dir):
    response = authorized_client.post("/upload/avatar", files=png())
    assert response.status_code == 200

    data = response.json()
    assert data["avatar_url"].startswith("/uploads/")
    assert data["avatar_url"].endswith(".png")

    filename = data["avatar_url"].split("/")[-1]
    assert (temp_upload_dir / filename).exists()

    # /auth/me ham avatarni qaytaradi
    me = authorized_client.get("/auth/me").json()
    assert me["avatar_url"] == data["avatar_url"]


def test_avatar_replace_deletes_old_file(authorized_client, temp_upload_dir):
    first = authorized_client.post("/upload/avatar", files=png()).json()
    second = authorized_client.post(
        "/upload/avatar", files={"file": ("yangi.jpg", b"new", "image/jpeg")}
    ).json()

    assert first["avatar_url"] != second["avatar_url"]
    files = [p.name for p in temp_upload_dir.iterdir()]
    assert files == [second["avatar_url"].split("/")[-1]]  # faqat yangisi qoldi


def test_avatar_rejects_wrong_type(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("matn.txt", b"salom", "text/plain")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []
    assert authorized_client.get("/auth/me").json()["avatar_url"] is None


def test_avatar_rejects_too_large(authorized_client, monkeypatch, temp_upload_dir):
    monkeypatch.setattr(upload_module, "MAX_SIZE", 10)
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("katta.png", b"x" * 20, "image/png")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []