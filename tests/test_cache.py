from datetime import datetime

import pytest
import redis

from app import cache


def test_set_and_get_roundtrip():
    assert cache.cache_set("k", {"a": 1, "b": [1, 2]}) is True
    assert cache.cache_get("k") == {"a": 1, "b": [1, 2]}


def test_get_missing_returns_none():
    assert cache.cache_get("yoq") is None


def test_empty_list_is_cached_not_a_miss():
    # Bo'sh ro'yxat ham haqiqiy qiymat: "cache yo'q" bilan adashtirilmasin
    cache.cache_set("bosh", [])
    assert cache.cache_get("bosh") == []


def test_set_uses_given_ttl(fake_redis):
    cache.cache_set("k", 1, ttl=60)
    assert 0 < fake_redis.ttl("k") <= 60


def test_set_uses_default_ttl(fake_redis):
    cache.cache_set("k", 1)
    assert 0 < fake_redis.ttl("k") <= cache.CACHE_TTL


def test_delete():
    cache.cache_set("k", 1)
    assert cache.cache_delete("k") is True
    assert cache.cache_get("k") is None


def test_delete_pattern_only_matching_keys():
    cache.cache_set("foods:1", 1)
    cache.cache_set("foods:all", 2)
    cache.cache_set("restaurants:1", 3)

    assert cache.cache_delete_pattern("foods:*") == 2
    assert cache.cache_get("foods:1") is None
    assert cache.cache_get("foods:all") is None
    assert cache.cache_get("restaurants:1") == 3


def test_datetime_is_serialized():
    cache.cache_set("vaqt", {"at": datetime(2026, 1, 1, 12, 0)})
    assert cache.cache_get("vaqt") == {"at": "2026-01-01 12:00:00"}


def test_api_survives_when_redis_is_down(monkeypatch):
    class Broken:
        def __getattr__(self, name):
            def fail(*args, **kwargs):
                raise redis.ConnectionError("Redis o'chiq")
            return fail

    monkeypatch.setattr(cache, "redis_client", Broken())

    assert cache.cache_get("k") is None
    assert cache.cache_set("k", 1) is False
    assert cache.cache_delete("k") is False
    assert cache.cache_delete_pattern("*") == 0
    assert cache.redis_ok() is False    