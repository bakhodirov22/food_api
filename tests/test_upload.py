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


def test_image_endpoint_rejects_pdf(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/image",
        files={"file": ("hujjat.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []


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


# ─── /upload/file (rasm, PDF, video) ──────────────────────────────────
def test_file_requires_auth(client):
    response = client.post(
        "/upload/file", files={"file": ("a.pdf", b"%PDF", "application/pdf")}
    )
    assert response.status_code == 401


def test_file_pdf_success(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/file",
        files={"file": ("hujjat.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["filename"].endswith(".pdf")
    assert data["kind"] == "application"
    assert data["content_type"] == "application/pdf"
    assert data["size"] == len(b"%PDF-1.4 test")
    assert (temp_upload_dir / data["filename"]).exists()


def test_file_video_success(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/file",
        files={"file": ("kino.mp4", b"fake-video", "video/mp4")},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["filename"].endswith(".mp4")
    assert data["kind"] == "video"
    assert (temp_upload_dir / data["filename"]).exists()


def test_file_image_success(authorized_client):
    response = authorized_client.post("/upload/file", files=png())
    assert response.status_code == 200
    assert response.json()["kind"] == "image"


def test_file_rejects_wrong_type(authorized_client, temp_upload_dir):
    for name, content_type in [
        ("matn.txt", "text/plain"),
        ("dastur.exe", "application/x-msdownload"),
        ("audio.mp3", "audio/mpeg"),
    ]:
        response = authorized_client.post(
            "/upload/file", files={"file": (name, b"data", content_type)}
        )
        assert response.status_code == 400

    assert list(temp_upload_dir.iterdir()) == []


def test_file_pdf_too_large(authorized_client, monkeypatch, temp_upload_dir):
    monkeypatch.setattr(
        upload_module,
        "MAX_SIZES",
        {"image": 10, "application": 10, "video": 100},
    )
    response = authorized_client.post(
        "/upload/file",
        files={"file": ("katta.pdf", b"x" * 20, "application/pdf")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []


def test_file_video_has_its_own_limit(authorized_client, monkeypatch):
    # PDF limiti 10 bayt, video limiti 100 bayt: 20 baytlik video o'tadi,
    # 20 baytlik PDF o'tmaydi
    monkeypatch.setattr(
        upload_module,
        "MAX_SIZES",
        {"image": 10, "application": 10, "video": 100},
    )
    video = authorized_client.post(
        "/upload/file",
        files={"file": ("kino.mp4", b"x" * 20, "video/mp4")},
    )
    pdf = authorized_client.post(
        "/upload/file",
        files={"file": ("hujjat.pdf", b"x" * 20, "application/pdf")},
    )
    assert video.status_code == 200
    assert pdf.status_code == 400


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


def test_avatar_rejects_pdf(authorized_client, temp_upload_dir):
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("hujjat.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []


def test_avatar_rejects_too_large(authorized_client, monkeypatch, temp_upload_dir):
    monkeypatch.setattr(upload_module, "MAX_SIZE", 10)
    response = authorized_client.post(
        "/upload/avatar",
        files={"file": ("katta.png", b"x" * 20, "image/png")},
    )
    assert response.status_code == 400
    assert list(temp_upload_dir.iterdir()) == []