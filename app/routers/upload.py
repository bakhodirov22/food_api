import os
import uuid

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
ALLOWED_TYPES = set(EXTENSIONS)
MAX_SIZE = 5 * 1024 * 1024  # 5 MB


async def read_valid_image(file: UploadFile) -> bytes:
    """Turi va hajmini tekshirib, fayl mazmunini qaytaradi."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat rasm formatlari: jpeg, png, gif, webp",
        )
    contents = await file.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fayl hajmi 5 MB dan oshmasin",
        )
    return contents


async def save_file(contents: bytes, content_type: str) -> str:
    """Faylni diskka yozadi va noyob fayl nomini qaytaradi."""
    filename = f"{uuid.uuid4()}.{EXTENSIONS[content_type]}"
    async with aiofiles.open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        await f.write(contents)
    return filename


def delete_old_file(url: str | None):
    """'/uploads/abc.png' ko'rinishidagi url bo'yicha eski faylni o'chiradi."""
    if not url:
        return
    path = os.path.join(UPLOAD_DIR, os.path.basename(url))
    if os.path.isfile(path):
        os.remove(path)


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
):
    contents = await read_valid_image(file)
    filename = await save_file(contents, file.content_type)
    return {
        "filename": filename,
        "url": f"/uploads/{filename}",
        "size": len(contents),
        "content_type": file.content_type,
    }


@router.post("/images")
async def upload_multiple(
    files: list[UploadFile] = File(...),
    current_user: models.User = Depends(get_current_user),
):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Bir vaqtda max 5 ta fayl")

    results = []
    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            continue
        contents = await file.read()
        if len(contents) > MAX_SIZE:
            continue
        filename = await save_file(contents, file.content_type)
        results.append(
            {"filename": filename, "url": f"/uploads/{filename}", "size": len(contents)}
        )

    return {"uploaded": results, "count": len(results)}


@router.post("/avatar", response_model=schemas.UserOut)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    contents = await read_valid_image(file)
    filename = await save_file(contents, file.content_type)

    old_url = current_user.avatar_url
    current_user.avatar_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(current_user)

    delete_old_file(old_url)  # yangisi saqlangandan keyin eskisini o'chiramiz
    return current_user