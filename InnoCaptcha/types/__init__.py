"""
captcha_lib.types
~~~~~~~~~~~~~~~~~
Plugin registry for CAPTCHA type plugins.

Usage::

    from captcha_lib.types import register_plugin, get_plugin, list_plugins

    @register_plugin("my_type")
    class MyCaptcha(CaptchaBase):
        ...

    cls = get_plugin("my_type")
    available = list_plugins()
"""

from __future__ import annotations

import importlib
import logging
from typing import Dict, List, Type

from ..core.base import CaptchaBase
from ..core.exceptions import PluginAlreadyRegisteredError, PluginNotFoundError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_registry: Dict[str, Type[CaptchaBase]] = {}

# Built-in plugins to auto-import (lazy, to avoid circular deps)
_BUILTIN_MODULES = [
    "captcha_lib.types.image",
    "captcha_lib.types.math",
]


def _ensure_builtins_loaded() -> None:
    """Import built-in plugin modules so their decorators run."""
    for module_path in _BUILTIN_MODULES:
        parts = module_path.split(".")
        # Convert absolute module path to relative package path
        try:
            importlib.import_module("." + ".".join(parts[1:]), package="captcha_lib")
        except ImportError:
            pass  # optional builtins — skip gracefully


# ---------------------------------------------------------------------------
# Public registry API
# ---------------------------------------------------------------------------


def register_plugin(name: str, *, overwrite: bool = False):
    """Class decorator that registers a :class:`~captcha_lib.core.base.CaptchaBase`
    subclass under *name*.

    Args:
        name:      Registry key (e.g. ``"image"``, ``"math"``).
        overwrite: If ``True``, silently replace any existing plugin with the
                   same name.  Defaults to ``False``.

    Returns:
        The decorator function.

    Raises:
        PluginAlreadyRegisteredError: If *name* is taken and *overwrite* is ``False``.
        TypeError: If the decorated class is not a subclass of :class:`CaptchaBase`.

    Example::

        @register_plugin("audio")
        class AudioCaptcha(CaptchaBase):
            ...
    """

    def decorator(cls: Type[CaptchaBase]) -> Type[CaptchaBase]:
        if not (isinstance(cls, type) and issubclass(cls, CaptchaBase)):
            raise TypeError(
                f"register_plugin: {cls!r} must be a subclass of CaptchaBase."
            )
        if name in _registry and not overwrite:
            raise PluginAlreadyRegisteredError(name)
        _registry[name] = cls
        logger.debug("Plugin registered: %r -> %s", name, cls.__qualname__)
        return cls

    return decorator


def get_plugin(name: str) -> Type[CaptchaBase]:
    """Look up a registered plugin class by name.

    Args:
        name: Registry key.

    Returns:
        The plugin class.

    Raises:
        PluginNotFoundError: If *name* is not registered.
    """
    if not _registry:
        _ensure_builtins_loaded()
    if name not in _registry:
        raise PluginNotFoundError(name)
    return _registry[name]


def list_plugins() -> List[str]:
    """Return the names of all currently registered plugins.

    Returns:
        Sorted list of plugin name strings.
    """
    if not _registry:
        _ensure_builtins_loaded()
    return sorted(_registry.keys())


def unregister_plugin(name: str) -> None:
    """Remove a plugin from the registry.

    Args:
        name: Registry key to remove.

    Raises:
        PluginNotFoundError: If *name* is not registered.
    """
    if name not in _registry:
        raise PluginNotFoundError(name)
    del _registry[name]
    logger.debug("Plugin unregistered: %r", name)
