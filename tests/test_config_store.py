from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_feature_flags.config_store import FileConfigStore, RedisConfigStore, get_config_store
from ai_feature_flags.schema import FlagDefinition, FlagType

TS = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _flag(key: str = "rag.enabled", **overrides) -> FlagDefinition:
    base = dict(
        key=key,
        type=FlagType.BOOLEAN,
        default_value=False,
        description="toggle rag",
        owner="platform-ai",
        created_at=TS,
        updated_at=TS,
    )
    base.update(overrides)
    return FlagDefinition(**base)


@pytest.fixture
def file_store(tmp_path):
    return FileConfigStore(tmp_path / "flags")


@pytest.fixture
def redis_store():
    fakeredis = pytest.importorskip("fakeredis")
    return RedisConfigStore(fakeredis.FakeStrictRedis())


# Both backends must satisfy the exact same contract - the fixture name is
# parametrized so every test below runs once per backend.
@pytest.fixture(params=["file_store", "redis_store"])
def store(request):
    return request.getfixturevalue(request.param)


def test_get_missing_flag_returns_none(store):
    assert store.get("does.not.exist") is None


def test_set_then_get_round_trips(store):
    flag = _flag()
    store.set(flag)
    fetched = store.get(flag.key)
    assert fetched is not None
    assert fetched.key == flag.key
    assert fetched.default_value is False
    assert fetched.type == FlagType.BOOLEAN


def test_set_overwrites_existing_flag(store):
    store.set(_flag(description="first"))
    store.set(_flag(description="second"))
    assert store.get("rag.enabled").description == "second"


def test_list_returns_all_flags_sorted_by_key(store):
    store.set(_flag(key="voice_agent.max_turns", type=FlagType.NUMBER, default_value=12))
    store.set(_flag(key="llm.provider", type=FlagType.STRING, default_value="anthropic"))
    store.set(_flag(key="rag.enabled"))

    keys = [flag.key for flag in store.list()]
    assert keys == ["llm.provider", "rag.enabled", "voice_agent.max_turns"]


def test_list_on_empty_store_returns_empty_list(store):
    assert store.list() == []


def test_delete_removes_flag_and_reports_existence(store):
    store.set(_flag())
    assert store.delete("rag.enabled") is True
    assert store.get("rag.enabled") is None
    # Deleting again reports that nothing was there to remove.
    assert store.delete("rag.enabled") is False


def test_object_and_number_flags_round_trip(store):
    routing = _flag(
        key="voice_agent.routing_rules",
        type=FlagType.OBJECT,
        default_value={"default": "general_queue", "billing": "billing_queue"},
    )
    store.set(routing)
    fetched = store.get(routing.key)
    assert fetched.default_value == {"default": "general_queue", "billing": "billing_queue"}


# -- FileConfigStore-specific behavior --------------------------------------


def test_file_store_creates_base_dir(tmp_path):
    base_dir = tmp_path / "nested" / "flags"
    assert not base_dir.exists()
    FileConfigStore(base_dir)
    assert base_dir.is_dir()


def test_file_store_rejects_unsafe_keys(file_store):
    with pytest.raises(ValueError):
        file_store.get("../escape")
    with pytest.raises(ValueError):
        file_store.set(_flag(key="nested/path"))


def test_file_store_set_is_atomic_no_leftover_tmp_files(file_store, tmp_path):
    flag = _flag()
    file_store.set(flag)
    leftovers = list(file_store.base_dir.glob(".tmp-*"))
    assert leftovers == []
    # Only the real flag file should be present.
    assert [p.name for p in file_store.base_dir.glob("*.json")] == ["rag.enabled.json"]


# -- get_config_store() factory / fallback behavior --------------------------


def test_get_config_store_falls_back_to_file_when_redis_unreachable(tmp_path):
    store = get_config_store(redis_url="redis://localhost:1/0", file_dir=tmp_path / "flags")
    assert isinstance(store, FileConfigStore)


def test_get_config_store_uses_file_store_when_no_redis_url_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    store = get_config_store(file_dir=tmp_path / "flags")
    assert isinstance(store, FileConfigStore)


def test_get_config_store_uses_redis_when_reachable(monkeypatch, tmp_path):
    fakeredis = pytest.importorskip("fakeredis")
    redis = pytest.importorskip("redis")

    monkeypatch.setattr(redis.Redis, "from_url", lambda url, **kwargs: fakeredis.FakeStrictRedis())
    store = get_config_store(redis_url="redis://localhost:6379/0", file_dir=tmp_path / "flags")
    assert isinstance(store, RedisConfigStore)
