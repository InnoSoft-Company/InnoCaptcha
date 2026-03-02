"""
captcha_lib.core
~~~~~~~~~~~~~~~~~
Core abstractions and utilities.

Re-exports:
    CaptchaBase:     Abstract base class for all captcha plugins.
    StorageInterface: Abstract base class for storage backends.
    TokenValidator:  HMAC-based token issuer and validator.
    ImageCaptchaGenerator: Image rendering orchestrator.
    exceptions:      All custom exception types.
"""

from .base import CaptchaBase, StorageInterface
from .exceptions import (
    CaptchaAlreadyUsedError,
    CaptchaError,
    CaptchaExpiredError,
    CaptchaInvalidError,
    CaptchaMaxAttemptsError,
    ConfigurationError,
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
    RateLimitError,
    StorageConnectionError,
    StorageError,
    StorageKeyNotFoundError,
)
from .generator import ImageCaptchaGenerator
from .validator import TokenValidator

__all__ = [
    # Base classes
    "CaptchaBase",
    "StorageInterface",
    # Generator
    "ImageCaptchaGenerator",
    # Validator
    "TokenValidator",
    # Exceptions
    "CaptchaError",
    "CaptchaExpiredError",
    "CaptchaInvalidError",
    "CaptchaMaxAttemptsError",
    "CaptchaAlreadyUsedError",
    "StorageError",
    "StorageConnectionError",
    "StorageKeyNotFoundError",
    "PluginNotFoundError",
    "PluginAlreadyRegisteredError",
    "RateLimitError",
    "ConfigurationError",
]
