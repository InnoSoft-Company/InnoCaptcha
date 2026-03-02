"""
captcha_lib.storage
~~~~~~~~~~~~~~~~~~~~
Storage backend package.

Re-exports:
    MemoryStorage: Thread-safe in-memory backend.
    RedisStorage:  Redis backend (optional dependency).
"""

from .memory import MemoryStorage
from .redis import RedisStorage

__all__ = ["MemoryStorage", "RedisStorage"]
