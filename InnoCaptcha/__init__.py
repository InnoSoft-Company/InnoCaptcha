"""
captcha_lib
~~~~~~~~~~~~
Professional, pluggable CAPTCHA library for Python.

Quick start::

    from captcha_lib import Captcha

    # Simple image captcha
    captcha = Captcha.create()
    captcha.save("challenge.png")
    is_ok = captcha.verify(user_input)

    # Math captcha
    captcha = Captcha.create(captcha_type="math")
    captcha.save("math.png")
    is_ok = captcha.verify("11")

    # Advanced — hard difficulty, 8 chars, custom storage
    from captcha_lib.config import CaptchaConfig, DifficultyLevel
    from captcha_lib.storage import MemoryStorage

    cfg = CaptchaConfig(difficulty=DifficultyLevel.HARD, length=8)
    store = MemoryStorage()
    captcha = Captcha.create(config=cfg, storage=store)
    token = captcha.token
    image_bytes = captcha.bytes

    # Custom plugin  (see types/example_plugin.py for full template)
    from captcha_lib.types import register_plugin
    from captcha_lib.core import CaptchaBase

    @register_plugin("my_type")
    class MyCaptcha(CaptchaBase):
        ...

Public API surface
------------------
* :class:`Captcha`               — Factory / facade
* :class:`CaptchaConfig`         — Configuration dataclass
* :class:`DifficultyLevel`       — Difficulty enum
* :func:`register_plugin`        — Plugin decorator
* :func:`get_plugin`             — Plugin lookup
* :func:`list_plugins`           — Enumerate plugins
* :class:`MemoryStorage`         — Default storage backend
* All exception classes          — ``from captcha_lib.core import ...``
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from .config import CaptchaConfig, DifficultyLevel, OutputFormat, get_default_config
from .core.base import CaptchaBase, StorageInterface
from .core.exceptions import (
    CaptchaAlreadyUsedError,
    CaptchaError,
    CaptchaExpiredError,
    CaptchaInvalidError,
    CaptchaMaxAttemptsError,
    PluginNotFoundError,
    RateLimitError,
    StorageError,
)
from .storage.memory import MemoryStorage
from .types import get_plugin, list_plugins, register_plugin

if TYPE_CHECKING:
    from .storage.redis import RedisStorage

__version__ = "1.0.0"
__author__  = "captcha-lib contributors"
__license__ = "MIT"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default shared storage (module-level, swappable)
# ---------------------------------------------------------------------------
_default_storage: Optional[StorageInterface] = None


def set_default_storage(storage: StorageInterface) -> None:
    """Set the global default storage backend.

    When set, every :meth:`Captcha.create` call without an explicit *storage*
    argument will use this backend.

    Args:
        storage: Any :class:`~captcha_lib.core.base.StorageInterface` instance.
    """
    global _default_storage
    _default_storage = storage


# ---------------------------------------------------------------------------
# Captcha factory / facade
# ---------------------------------------------------------------------------


class Captcha:
    """High-level factory for creating and inspecting captcha instances.

    This class is the main entry point of the library.  It acts as a thin
    facade over the plugin registry and the individual captcha implementations.

    You never instantiate :class:`Captcha` directly — use :meth:`create`
    instead.

    Args:
        captcha_type: Name of the registered plugin (``"image"``, ``"math"``, …).
        difficulty:   Difficulty level preset.
        length:       Number of characters (image captcha only).
        width:        Image width in pixels.
        height:       Image height in pixels.
        expiry_seconds: Token TTL in seconds.
        max_attempts: Max verification attempts.
        case_sensitive: Whether answer matching is case-sensitive.
        secret_key:   HMAC secret key (auto-generated if omitted).

    Example::

        # Minimal
        captcha = Captcha.create()

        # Typed factory
        cfg = Captcha(type="math", difficulty="hard")
        captcha = Captcha.create(cfg)
    """

    # Config forwarding / shorthand construction --------------------------

    def __init__(
        self,
        captcha_type: str = "image",
        difficulty: str = "medium",
        length: Optional[int] = None,
        width: int = 160,
        height: int = 60,
        expiry_seconds: int = 300,
        max_attempts: int = 3,
        case_sensitive: bool = False,
        secret_key: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Build a :class:`CaptchaConfig` from keyword arguments."""
        self._config = CaptchaConfig(
            captcha_type=captcha_type,
            difficulty=DifficultyLevel(difficulty),
            length=length,
            width=width,
            height=height,
            expiry_seconds=expiry_seconds,
            max_attempts=max_attempts,
            case_sensitive=case_sensitive,
            secret_key=secret_key,
            **{k: v for k, v in kwargs.items() if hasattr(CaptchaConfig, k)},
        )

    @property
    def config(self) -> CaptchaConfig:
        """The :class:`CaptchaConfig` built from this instance's arguments."""
        return self._config

    # ------------------------------------------------------------------
    # Primary factory
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        config: Optional[CaptchaConfig] = None,
        storage: Optional[StorageInterface] = None,
        captcha_type: Optional[str] = None,
    ) -> CaptchaBase:
        """Create and generate a captcha instance.

        This is the canonical way to obtain a ready-to-use captcha.

        Args:
            config:       :class:`CaptchaConfig` to use.  Defaults to the
                          global default config.
            storage:      Storage backend.  Falls back to the global default
                          storage set via :func:`set_default_storage`, then
                          to an ephemeral :class:`MemoryStorage`.
            captcha_type: Override the plugin name (overrides ``config.captcha_type``).

        Returns:
            A generated :class:`CaptchaBase` subclass instance with
            :attr:`~CaptchaBase.token` populated.

        Raises:
            PluginNotFoundError: If the requested captcha type is not registered.

        Example::

            captcha = Captcha.create()                          # image, medium
            captcha = Captcha.create(captcha_type="math")       # math
            captcha = Captcha.create(config=CaptchaConfig.hard()) # hard difficulty
        """
        effective_config = config or get_default_config()
        effective_type   = captcha_type or effective_config.captcha_type
        if storage is not None:
            effective_storage: StorageInterface = storage
        elif _default_storage is not None:
            effective_storage = _default_storage
        else:
            effective_storage = MemoryStorage()

        plugin_cls = get_plugin(effective_type)
        instance: CaptchaBase = plugin_cls(config=effective_config, storage=effective_storage)
        instance.generate()

        logger.info(
            "Captcha.create: type=%r difficulty=%s id=%s",
            effective_type, effective_config.difficulty.value, instance.captcha_id,
        )
        return instance

    @classmethod
    async def create_async(
        cls,
        config: Optional[CaptchaConfig] = None,
        storage: Optional[StorageInterface] = None,
        captcha_type: Optional[str] = None,
    ) -> CaptchaBase:
        """Async variant of :meth:`create`.

        Runs image rendering off the event loop via ``asyncio.to_thread``.

        Args:
            config:       Configuration.
            storage:      Storage backend.
            captcha_type: Plugin name override.

        Returns:
            A generated captcha instance.
        """
        effective_config = config or get_default_config()
        effective_type   = captcha_type or effective_config.captcha_type
        if storage is not None:
            effective_storage: StorageInterface = storage
        elif _default_storage is not None:
            effective_storage = _default_storage
        else:
            effective_storage = MemoryStorage()

        plugin_cls = get_plugin(effective_type)
        instance: CaptchaBase = plugin_cls(config=effective_config, storage=effective_storage)

        # Call async generate if available, fall back to sync
        if hasattr(instance, "generate_async"):
            await instance.generate_async()
        else:
            instance.generate()

        return instance

    # ------------------------------------------------------------------
    # Convenience class-methods
    # ------------------------------------------------------------------

    @classmethod
    def image(cls, **kwargs) -> CaptchaBase:
        """Shortcut for ``Captcha.create(captcha_type="image", ...)``.

        Args:
            **kwargs: Forwarded to :class:`CaptchaConfig`.

        Returns:
            Generated image captcha.
        """
        return cls.create(config=CaptchaConfig(**kwargs), captcha_type="image")

    @classmethod
    def math(cls, **kwargs) -> CaptchaBase:
        """Shortcut for ``Captcha.create(captcha_type="math", ...)``.

        Args:
            **kwargs: Forwarded to :class:`CaptchaConfig`.

        Returns:
            Generated math captcha.
        """
        return cls.create(config=CaptchaConfig(**kwargs), captcha_type="math")

    @classmethod
    def plugins(cls) -> list:
        """Return the names of all registered captcha plugins.

        Returns:
            Sorted list of plugin name strings.
        """
        return list_plugins()


# ---------------------------------------------------------------------------
# Public __all__
# ---------------------------------------------------------------------------

__all__ = [
    # Factory
    "Captcha",
    # Config
    "CaptchaConfig",
    "DifficultyLevel",
    "OutputFormat",
    "get_default_config",
    "set_default_storage",
    # Plugin system
    "register_plugin",
    "get_plugin",
    "list_plugins",
    # Abstractions
    "CaptchaBase",
    "StorageInterface",
    # Storage
    "MemoryStorage",
    # Exceptions
    "CaptchaError",
    "CaptchaExpiredError",
    "CaptchaInvalidError",
    "CaptchaMaxAttemptsError",
    "CaptchaAlreadyUsedError",
    "PluginNotFoundError",
    "StorageError",
    "RateLimitError",
    # Meta
    "__version__",
]
