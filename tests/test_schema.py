from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from ai_feature_flags.examples import example_flags
from ai_feature_flags.schema import FlagDefinition, FlagType

TS = datetime(2025, 1, 1, tzinfo=timezone.utc)


def _flag(**overrides) -> dict:
    base = dict(
        key="rag.enabled",
        type=FlagType.BOOLEAN,
        default_value=False,
        description="toggle rag",
        owner="platform-ai",
        created_at=TS,
        updated_at=TS,
    )
    base.update(overrides)
    return base


@pytest.mark.parametrize("flag_type,default_value", [
    (FlagType.BOOLEAN, True),
    (FlagType.STRING, "v3"),
    (FlagType.NUMBER, 12),
    (FlagType.NUMBER, 1.5),
    (FlagType.OBJECT, {"a": 1}),
])
def test_valid_default_value_per_type(flag_type, default_value):
    flag = FlagDefinition(**_flag(type=flag_type, default_value=default_value))
    assert flag.default_value == default_value


def test_round_trip_json_serialization():
    original = FlagDefinition(**_flag())
    restored = FlagDefinition.from_json(original.to_json())
    assert restored == original


@pytest.mark.parametrize("flag_type,bad_default", [
    (FlagType.BOOLEAN, "yes"),
    (FlagType.STRING, 42),
    (FlagType.NUMBER, "12"),
    (FlagType.NUMBER, True),  # bool must not pass as a number despite bool <: int
    (FlagType.OBJECT, [1, 2]),
])
def test_default_value_type_mismatch_is_rejected(flag_type, bad_default):
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(type=flag_type, default_value=bad_default))


def test_key_with_whitespace_is_rejected():
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(key="rag enabled"))


def test_updated_before_created_is_rejected():
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(updated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)))


def test_missing_owner_is_rejected():
    payload = _flag()
    del payload["owner"]
    with pytest.raises(ValidationError):
        FlagDefinition(**payload)


def test_empty_owner_is_rejected():
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(owner=""))


def test_missing_description_is_rejected():
    payload = _flag()
    del payload["description"]
    with pytest.raises(ValidationError):
        FlagDefinition(**payload)


def test_unknown_type_is_rejected():
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(type="not-a-real-type"))


def test_empty_key_is_rejected():
    with pytest.raises(ValidationError):
        FlagDefinition(**_flag(key=""))


def test_example_flags_cover_every_type():
    types = {flag.type for flag in example_flags()}
    assert types == set(FlagType)


def test_example_flags_are_all_individually_valid():
    for flag in example_flags():
        # Constructing didn't raise, but round-trip through JSON too so the
        # documented examples stay parseable, not just constructible in-process.
        assert FlagDefinition.from_json(flag.to_json()) == flag
