"""Flag configuration store.

Redis is the primary backend for production/shared deployments; a JSON-file
store under ``configs/`` is the local-dev fallback used when Redis is not
configured or not reachable. Both backends implement the same ``ConfigStore``
protocol (get/set/list/delete) so callers never branch on which one is live.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Protocol, runtime_checkable

from ai_feature_flags.schema import FlagDefinition

logger = logging.getLogger(__name__)

DEFAULT_FILE_STORE_DIR = "configs/flags"


@runtime_checkable
class ConfigStore(Protocol):
    """Storage backend for flag definitions, keyed by ``FlagDefinition.key``."""

    def get(self, key: str) -> FlagDefinition | None:
        """Return the flag for ``key``, or ``None`` if it doesn't exist."""
        ...

    def set(self, flag: FlagDefinition) -> None:
        """Create or overwrite the flag at ``flag.key``."""
        ...

    def list(self) -> list[FlagDefinition]:
        """Return all stored flags, ordered by key."""
        ...

    def delete(self, key: str) -> bool:
        """Remove the flag at ``key``. Returns whether it existed."""
        ...


def _safe_filename(key: str) -> str:
    # Flag keys look like "rag.enabled" / "llm.provider" - safe for filenames -
    # but this is sanitized defensively so a stored key can never traverse
    # outside base_dir.
    if not key or "/" in key or "\\" in key or key in (".", ".."):
        raise ValueError(f"unsafe flag key for file storage: {key!r}")
    return f"{key}.json"


class FileConfigStore:
    """One JSON file per flag under a base directory. Local-dev fallback."""

    def __init__(self, base_dir: str | Path = DEFAULT_FILE_STORE_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.base_dir / _safe_filename(key)

    def get(self, key: str) -> FlagDefinition | None:
        path = self._path(key)
        if not path.exists():
            return None
        return FlagDefinition.from_json(path.read_text(encoding="utf-8"))

    def set(self, flag: FlagDefinition) -> None:
        path = self._path(flag.key)
        # Write-then-rename so a failure mid-write (disk full, interrupted
        # process) never leaves a truncated flag file at the real path.
        fd, tmp_name = tempfile.mkstemp(dir=self.base_dir, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(flag.to_json())
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def list(self) -> list[FlagDefinition]:
        flags = []
        for path in sorted(self.base_dir.glob("*.json")):
            if path.name.startswith(".tmp-"):
                continue
            flags.append(FlagDefinition.from_json(path.read_text(encoding="utf-8")))
        return sorted(flags, key=lambda flag: flag.key)

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not path.exists():
            return False
        path.unlink()
        return True


class RedisConfigStore:
    """Redis-backed store: one string key per flag under a namespace prefix."""

    KEY_PREFIX = "ai_feature_flags:flag:"

    def __init__(self, client):
        self._client = client

    def _redis_key(self, key: str) -> str:
        return f"{self.KEY_PREFIX}{key}"

    @staticmethod
    def _decode(raw: bytes | str) -> str:
        return raw.decode("utf-8") if isinstance(raw, bytes) else raw

    def get(self, key: str) -> FlagDefinition | None:
        raw = self._client.get(self._redis_key(key))
        if raw is None:
            return None
        return FlagDefinition.from_json(self._decode(raw))

    def set(self, flag: FlagDefinition) -> None:
        self._client.set(self._redis_key(flag.key), flag.to_json())

    def list(self) -> list[FlagDefinition]:
        flags = []
        for redis_key in self._client.keys(f"{self.KEY_PREFIX}*"):
            raw = self._client.get(redis_key)
            if raw is None:
                continue
            flags.append(FlagDefinition.from_json(self._decode(raw)))
        return sorted(flags, key=lambda flag: flag.key)

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(self._redis_key(key)))


def get_config_store(
    *,
    redis_url: str | None = None,
    file_dir: str | Path = DEFAULT_FILE_STORE_DIR,
) -> ConfigStore:
    """Return a Redis-backed store if reachable, else the file fallback.

    ``redis_url`` (or the ``REDIS_URL`` env var when not passed explicitly) is
    the intended backend. If Redis cannot be reached at construction time -
    no server running, wrong URL, the ``redis`` package missing - this logs a
    warning and falls back to ``FileConfigStore`` rather than failing startup,
    since local dev without a running Redis instance is a supported case. When
    no Redis URL is configured at all, the file store is used directly with no
    connection attempt.
    """
    redis_url = redis_url if redis_url is not None else os.environ.get("REDIS_URL")
    if redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            return RedisConfigStore(client)
        except Exception as exc:
            logger.warning(
                "Redis unavailable at %s (%s); falling back to file store at %s",
                redis_url,
                exc,
                file_dir,
            )
    return FileConfigStore(file_dir)
