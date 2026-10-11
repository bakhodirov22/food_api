# Food Delivery API

FastAPI + SQLAlchemy + PostgreSQL asosida restoranlar, taomlar va buyurtmalarni boshqaradigan backend API.

## Imkoniyatlar
- Ro'yxatdan o'tish va login (JWT)
- Restaurant va Food CRUD
- Restaurant bo'yicha filter
- Savat (cart)
- Order yaratish (jami narx avtomatik hisoblanadi)
- Order statusini o'zgartirish

## Lokal ishga tushirish

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger hujjat: http://127.0.0.1:8000/docs

## Deploy (AWS EC2)
Server sozlash bosqichlari `SETUP.md` da.
`main` branch'ga push qilinganda GitHub Actions serverni avtomatik yangilaydi.

## Texnologiyalar
FastAPI, SQLAlchemy, PostgreSQL, Pydantic, JWT, bcrypt, Gunicorn, Nginx