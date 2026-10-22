from sqlalchemy import text

from app.database import engine

with engine.begin() as conn:
    conn.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR"))

print("avatar_url ustuni qo'shildi!")