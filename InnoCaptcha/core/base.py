"""
captcha_lib.core.base
~~~~~~~~~~~~~~~~~~~~~
Abstract base classes that define the contracts every captcha type and
storage backend must satisfy.

Implementing these interfaces allows new captcha types and storage backends
to be dropped in without modifying any core library code (Open/Closed
Principle).
"""

from __future__ import annotations

import abc
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CaptchaBase
# ---------------------------------------------------------------------------


class CaptchaBase(abc.ABC):
    """Abstract contract that every captcha plugin must implement.

    Subclasses registered via :func:`~captcha_lib.types.register_plugin`
    become available through the :class:`~captcha_lib.Captcha` factory.

    Attributes:
        token:        Signed token representing this captcha instance.
        captcha_id:   Unique identifier for this instance.
        answer_hash:  SHA-256 hash of the correct answer.
        attempts:     Number of verification attempts so far.
        is_verified:  Whether the captcha has been successfully solved.
    """

    def __init__(self, config: Any) -> None:
        """Initialise common captcha state.

        Args:
            config: A :class:`~captcha_lib.config.CaptchaConfig` instance.
        """
        self._config = config
        self.token: Optional[str] = None
        self.captcha_id: str = ""
        self.answer_hash: str = ""
        self.attempts: int = 0
        self.is_verified: bool = False

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def generate(self) -> "CaptchaBase":
        """Generate the captcha challenge.

        This method must populate ``self.token``, ``self.captcha_id``, and
        ``self.answer_hash``, then return *self* to enable chaining.

        Returns:
            This instance (for method chaining).
        """

    @abc.abstractmethod
    def verify(self, answer: str) -> bool:
        """Check whether *answer* correctly solves this captcha.

        Implementations should:
        - Increment ``self.attempts``
        - Raise :exc:`~captcha_lib.core.exceptions.CaptchaExpiredError` if expired
        - Raise :exc:`~captcha_lib.core.exceptions.CaptchaMaxAttemptsError` if limit reached
        - Set ``self.is_verified = True`` on success
        - Raise :exc:`~captcha_lib.core.exceptions.CaptchaAlreadyUsedError` if replayed

        Args:
            answer: User-supplied answer string.

        Returns:
            ``True`` if the answer is correct, ``False`` otherwise.
        """

    @abc.abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialise this captcha instance to a JSON-safe dictionary.

        Returns:
            A dictionary suitable for JSON serialisation.
        """

    @abc.abstractmethod
    def get_image(self) -> Optional[Any]:
        """Return the challenge image (if this captcha type produces one).

        Returns:
            A :class:`PIL.Image.Image` or ``None`` for non-image types.
        """

    # ------------------------------------------------------------------
    # Concrete helpers
    # ------------------------------------------------------------------

    @property
    def config(self) -> Any:
        """Read-only access to the captcha configuration."""
        return self._config

    def __repr__(self) -> str:
        cls = self.__class__.__name__
        return (
            f"<{cls} id={self.captcha_id!r} verified={self.is_verified} "
            f"attempts={self.attempts}>"
        )


# ---------------------------------------------------------------------------
# StorageInterface
# ---------------------------------------------------------------------------


class StorageInterface(abc.ABC):
    """Abstract contract for captcha state persistence backends.

    Implementations must be thread-safe (or coroutine-safe for async
    backends).  The library ships :class:`~captcha_lib.storage.memory.MemoryStorage`
    and :class:`~captcha_lib.storage.redis.RedisStorage`.
    """

    @abc.abstractmethod
    def save(self, key: str, value: Dict[str, Any], ttl: int = 300) -> None:
        """Persist *value* under *key* with an optional time-to-live.

        Args:
            key:   Unique identifier (typically ``captcha_id``).
            value: JSON-serialisable dictionary to store.
            ttl:   Seconds until automatic expiry (0 = no expiry).
        """

    @abc.abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve a previously saved value.

        Args:
            key: Unique identifier used during :meth:`save`.

        Returns:
            The stored dictionary, or ``None`` if missing or expired.
        """

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        """Remove the entry for *key* from the store.

        Args:
            key: Unique identifier to remove.

        Raises:
            :exc:`~captcha_lib.core.exceptions.StorageKeyNotFoundError`:
                if the key does not exist.
        """

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        """Check whether *key* is present and has not expired.

        Args:
            key: Unique identifier to check.

        Returns:
            ``True`` if the key exists and is not expired.
        """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"
