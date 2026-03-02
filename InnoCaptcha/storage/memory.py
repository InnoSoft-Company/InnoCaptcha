"""
captcha_lib.storage.memory
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Thread-safe in-memory storage backend with TTL-based expiry.

Suitable for single-process deployments, development, and testing.
For multi-process or distributed setups use
:class:`~captcha_lib.storage.redis.RedisStorage` instead.
"""

from __future__ import annotations

import logging
import time
import threading
from typing import Any, Dict, Optional

from ..core.base import StorageInterface
from ..core.exceptions import StorageKeyNotFoundError

logger = logging.getLogger(__name__)


class MemoryStorage(StorageInterface):
    """Dictionary-backed in-memory captcha store with automatic TTL expiry.

    All public methods acquire a :class:`threading.Lock` before accessing
    the internal store, making this class safe to use from multiple threads.

    Args:
        max_size: Maximum number of entries to retain.  When exceeded, the
                  oldest entries are evicted (LRU-style).  ``0`` = unlimited.

    Example::

        store = MemoryStorage(max_size=1000)
        captcha = Captcha.create(storage=store)
    """

    def __init__(self, max_size: int = 0) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._max_size = max_size

    # ------------------------------------------------------------------
    # StorageInterface implementation
    # ------------------------------------------------------------------

    def save(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Store *value* under *key* with a TTL.

        Args:
            key:   Unique captcha identifier.
            value: JSON-serialisable state dictionary.
            ttl:   Time-to-live in seconds.  ``0`` means no expiry.
        """
        with self._lock:
            self._evict_expired()
            if self._max_size and len(self._store) >= self._max_size:
                # Evict oldest
                oldest_key = next(iter(self._store))
                del self._store[oldest_key]
                logger.debug("MemoryStorage max_size reached — evicted key=%r", oldest_key)
            self._store[key] = {
                "_value": value,
                "_expires_at": time.monotonic() + ttl if ttl > 0 else None,
            }
            logger.debug("MemoryStorage.save key=%r ttl=%ds", key, ttl)

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve the value for *key*, or ``None`` if missing or expired.

        Args:
            key: Unique captcha identifier.

        Returns:
            Stored dictionary, or ``None``.
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at = entry["_expires_at"]
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                logger.debug("MemoryStorage.load key=%r expired — removed", key)
                return None
            return entry["_value"]

    def delete(self, key: str) -> None:
        """Remove the entry for *key*.

        Args:
            key: Key to delete.

        Raises:
            StorageKeyNotFoundError: If *key* does not exist.
        """
        with self._lock:
            if key not in self._store:
                raise StorageKeyNotFoundError(key)
            del self._store[key]
            logger.debug("MemoryStorage.delete key=%r", key)

    def exists(self, key: str) -> bool:
        """Check whether *key* exists and has not expired.

        Args:
            key: Key to check.

        Returns:
            ``True`` if the key is present and unexpired.
        """
        return self.load(key) is not None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        """Remove all expired entries (called internally, lock must be held)."""
        now = time.monotonic()
        expired = [
            k for k, v in self._store.items()
            if v["_expires_at"] is not None and now > v["_expires_at"]
        ]
        for k in expired:
            del self._store[k]
        if expired:
            logger.debug("MemoryStorage evicted %d expired entries", len(expired))

    def clear(self) -> None:
        """Remove all entries from the store."""
        with self._lock:
            self._store.clear()
            logger.debug("MemoryStorage cleared")

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

    def __repr__(self) -> str:
        return f"<MemoryStorage entries={len(self)} max_size={self._max_size}>"
