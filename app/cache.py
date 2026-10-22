import json
import logging
import os
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
CACHE_TTL = int(os.getenv("CACHE_TTL", "300"))  # 5 daqiqa (sekund)

# REDIS_URL bo'sh qilib qo'yilsa, cache butunlay o'chiriladi
redis_client = (
    redis.from_url(
        REDIS_URL,
        decode_responses=True,       # bytes o'rniga str qaytaradi
        protocol=2,                  # eski Redis serverlar uchun (HELLO yubormaydi)
        socket_connect_timeout=1,    # Redis yo'q bo'lsa uzoq kutmaydi
        socket_timeout=1,
    )
    if REDIS_URL
    else None
)


def redis_ok() -> bool:
    """Redis ga ulanish borligini tekshiradi."""
    if redis_client is None:
        return False
    try:
        return bool(redis_client.ping())
    except Exception:
        return False


def cache_get(key: str) -> Optional[Any]:
    """Qiymatni qaytaradi. Topilmasa yoki Redis ishlamasa None."""
    if redis_client is None:
        return None
    try:
        data = redis_client.get(key)
        return None if data is None else json.loads(data)
    except Exception as e:
        logger.warning(f"Cache get xato: {e}")
        return None


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Qiymatni TTL (sekund) bilan saqlaydi."""
    if redis_client is None:
        return False
    try:
        redis_client.setex(
            key,
            CACHE_TTL if ttl is None else ttl,
            json.dumps(value, default=str),  # datetime -> str
        )
        return True
    except Exception as e:
        logger.warning(f"Cache set xato: {e}")
        return False


def cache_delete(key: str) -> bool:
    if redis_client is None:
        return False
    try:
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete xato: {e}")
        return False


def cache_delete_pattern(pattern: str) -> int:
    """Pattern bo'yicha o'chiradi (masalan 'foods:*'). O'chirilganlar sonini qaytaradi."""
    if redis_client is None:
        return 0
    try:
        keys = list(redis_client.scan_iter(match=pattern))
        if keys:
            redis_client.delete(*keys)
        return len(keys)
    except Exception as e:
        logger.warning(f"Cache pattern delete xato: {e}")
        return 0