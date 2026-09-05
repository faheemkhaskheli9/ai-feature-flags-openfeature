"""Versioned flag definition schema.

Every flag in the system — prompt-version flags, LLM provider/model flags, RAG
toggle flags, voice-agent flags — is one ``FlagDefinition``. The flag *type*
picks which Python type ``default_value`` (and later, evaluated values) must
be; there is one type enum plus one model, not one Python field per flag kind,
so adding a new flag is a data change, not a code change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

SCHEMA_VERSION = 1


class FlagType(str, Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    OBJECT = "object"


_PYTHON_TYPES: dict[FlagType, tuple[type, ...]] = {
    FlagType.BOOLEAN: (bool,),
    # bool is a subclass of int in Python, so it's excluded explicitly here or
    # `True` would silently pass as a valid "number" default.
    FlagType.STRING: (str,),
    FlagType.NUMBER: (int, float),
    FlagType.OBJECT: (dict,),
}


def _matches_type(flag_type: FlagType, value: Any) -> bool:
    if flag_type == FlagType.NUMBER and isinstance(value, bool):
        return False
    return isinstance(value, _PYTHON_TYPES[flag_type])


class FlagDefinition(BaseModel):
    """A single versioned feature flag definition."""

    schema_version: int = SCHEMA_VERSION
    key: str = Field(min_length=1, description="unique flag identifier, e.g. 'rag.enabled'")
    type: FlagType
    default_value: Any
    description: str = Field(min_length=1)
    owner: str = Field(min_length=1, description="team or individual responsible for this flag")
    created_at: datetime
    updated_at: datetime

    @field_validator("key")
    @classmethod
    def _key_has_no_whitespace(cls, value: str) -> str:
        if value != value.strip() or " " in value:
            raise ValueError(f"key must not contain whitespace, got {value!r}")
        return value

    @model_validator(mode="after")
    def _default_value_matches_type(self) -> "FlagDefinition":
        if not _matches_type(self.type, self.default_value):
            raise ValueError(
                f"default_value {self.default_value!r} does not match type {self.type.value!r}"
            )
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be before created_at")
        return self

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> "FlagDefinition":
        return cls.model_validate_json(data)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
