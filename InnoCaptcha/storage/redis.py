"""
captcha_lib.storage.redis
~~~~~~~~~~~~~~~~~~~~~~~~~~
Optional Redis-backed storage backend.

Requires the ``redis`` package::

    pip install captcha-lib[redis]

The ``redis`` import is deferred so the library can be used without Redis
installed; a clear :exc:`ImportError` is raised only when
:class:`RedisStorage` is instantiated.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from ..core.base import StorageInterface
from ..core.exceptions import StorageConnectionError, StorageKeyNotFoundError

logger = logging.getLogger(__name__)


class RedisStorage(StorageInterface):
    """Redis-backed captcha storage with native TTL support.

    Each captcha is stored as a JSON string under its ``captcha_id`` key.
    Redis handles TTL expiry natively, so no in-process cleanup is needed.

    Args:
        client:      A ``redis.Redis`` (or ``redis.asyncio.Redis``) client.
        key_prefix:  Prepended to every key to namespace captcha entries.
                     Defaults to ``"captcha:"``.

    Example::

        import redis
        from captcha_lib.storage import RedisStorage

        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        store = RedisStorage(r)
        captcha = Captcha.create(storage=store)

    Raises:
        ImportError: If the ``redis`` package is not installed.
    """

    def __init__(self, client: Any, key_prefix: str = "captcha:") -> None:
        try:
            import redis as _redis  # noqa: F401 — just validate install
        except ImportError as exc:
            raise ImportError(
                "RedisStorage requires the 'redis' package. "
                "Install it with: pip install captcha-lib[redis]"
            ) from exc

        self._client = client
        self._prefix = key_prefix

    # ------------------------------------------------------------------
    # StorageInterface implementation
    # ------------------------------------------------------------------

    def save(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Persist *value* to Redis under *key* with a TTL.

        Args:
            key:   Captcha ID.
            value: JSON-serialisable state dictionary.
            ttl:   Expiry in seconds (passed directly to Redis ``EX``).
        """
        full_key = self._prefix + key
        try:
            serialised = json.dumps(value)
            if ttl > 0:
                self._client.setex(full_key, ttl, serialised)
            else:
                self._client.set(full_key, serialised)
            logger.debug("RedisStorage.save key=%r ttl=%ds", full_key, ttl)
        except Exception as exc:
            raise StorageConnectionError("redis") from exc

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve the stored value for *key*, or ``None`` if absent/expired.

        Args:
            key: Captcha ID.

        Returns:
            The stored dictionary, or ``None``.
        """
        full_key = self._prefix + key
        try:
            raw = self._client.get(full_key)
        except Exception as exc:
            raise StorageConnectionError("redis") from exc

        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("RedisStorage: malformed JSON for key=%r — ignoring", full_key)
            return None

    def delete(self, key: str) -> None:
        """Remove *key* from Redis.

        Args:
            key: Captcha ID to delete.

        Raises:
            StorageKeyNotFoundError: If the key does not exist in Redis.
        """
        full_key = self._prefix + key
        try:
            deleted = self._client.delete(full_key)
        except Exception as exc:
            raise StorageConnectionError("redis") from exc

        if not deleted:
            raise StorageKeyNotFoundError(key)
        logger.debug("RedisStorage.delete key=%r", full_key)

    def exists(self, key: str) -> bool:
        """Check whether *key* exists in Redis.

        Args:
            key: Captcha ID.

        Returns:
            ``True`` if the key is present (and not expired by Redis).
        """
        full_key = self._prefix + key
        try:
            return bool(self._client.exists(full_key))
        except Exception as exc:
            raise StorageConnectionError("redis") from exc

    def __repr__(self) -> str:
        return f"<RedisStorage prefix={self._prefix!r}>"
