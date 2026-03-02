"""
captcha_lib.core.exceptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Custom exception hierarchy for the CAPTCHA library.

All library errors inherit from ``CaptchaError`` so callers can
catch a single base type if they prefer.
"""


class CaptchaError(Exception):
    """Base exception for all captcha-lib errors."""

    def __init__(self, message: str = "", code: str = "CAPTCHA_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.code!r}, message={self.message!r})"


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


class CaptchaExpiredError(CaptchaError):
    """Raised when a captcha token has passed its expiration time."""

    def __init__(self, message: str = "Captcha has expired.") -> None:
        super().__init__(message, code="CAPTCHA_EXPIRED")


class CaptchaInvalidError(CaptchaError):
    """Raised when a captcha answer or token is invalid."""

    def __init__(self, message: str = "Captcha answer is invalid.") -> None:
        super().__init__(message, code="CAPTCHA_INVALID")


class CaptchaMaxAttemptsError(CaptchaError):
    """Raised when the maximum number of verification attempts is exceeded."""

    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(
            f"Maximum verification attempts ({max_attempts}) exceeded.",
            code="CAPTCHA_MAX_ATTEMPTS",
        )
        self.max_attempts = max_attempts


class CaptchaAlreadyUsedError(CaptchaError):
    """Raised when a single-use token is replayed after successful verification."""

    def __init__(self, message: str = "Captcha token has already been used.") -> None:
        super().__init__(message, code="CAPTCHA_REPLAY")


# ---------------------------------------------------------------------------
# Storage errors
# ---------------------------------------------------------------------------


class StorageError(CaptchaError):
    """Base class for storage backend errors."""

    def __init__(self, message: str = "Storage operation failed.", cause: Exception | None = None) -> None:
        super().__init__(message, code="STORAGE_ERROR")
        self.__cause__ = cause


class StorageConnectionError(StorageError):
    """Raised when the storage backend is unreachable."""

    def __init__(self, backend: str = "unknown") -> None:
        super().__init__(f"Cannot connect to storage backend: {backend}.")
        self.code = "STORAGE_CONNECTION_ERROR"


class StorageKeyNotFoundError(StorageError):
    """Raised when a requested key does not exist in storage."""

    def __init__(self, key: str = "") -> None:
        super().__init__(f"Key not found in storage: {key!r}.")
        self.code = "STORAGE_KEY_NOT_FOUND"


# ---------------------------------------------------------------------------
# Plugin errors
# ---------------------------------------------------------------------------


class PluginNotFoundError(CaptchaError):
    """Raised when a requested captcha type plugin is not registered."""

    def __init__(self, plugin_name: str) -> None:
        super().__init__(
            f"No captcha plugin registered under name: {plugin_name!r}.",
            code="PLUGIN_NOT_FOUND",
        )
        self.plugin_name = plugin_name


class PluginAlreadyRegisteredError(CaptchaError):
    """Raised when attempting to register a plugin name that already exists."""

    def __init__(self, plugin_name: str) -> None:
        super().__init__(
            f"A plugin is already registered under name: {plugin_name!r}.",
            code="PLUGIN_ALREADY_REGISTERED",
        )
        self.plugin_name = plugin_name


# ---------------------------------------------------------------------------
# Rate limiting errors
# ---------------------------------------------------------------------------


class RateLimitError(CaptchaError):
    """Raised when a client exceeds the allowed request rate."""

    def __init__(self, retry_after: float = 60.0) -> None:
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after:.0f} seconds.",
            code="RATE_LIMIT_EXCEEDED",
        )
        self.retry_after = retry_after


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------


class ConfigurationError(CaptchaError):
    """Raised when invalid configuration values are provided."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(
            f"Invalid configuration for field '{field}': {reason}",
            code="CONFIGURATION_ERROR",
        )
        self.field = field
