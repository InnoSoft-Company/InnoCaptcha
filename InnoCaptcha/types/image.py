"""
captcha_lib.types.image
~~~~~~~~~~~~~~~~~~~~~~~~
Image-text CAPTCHA plugin — a production-quality refactoring of the
original ``image.py`` implementation.

Registered under the key ``"image"`` in the plugin registry.
"""

from __future__ import annotations

import io
import logging
import secrets
from typing import Any, Dict, Optional

from PIL.Image import Image

from ..config import CaptchaConfig, OutputFormat, get_default_config
from ..core.base import CaptchaBase
from ..core.exceptions import (
    CaptchaAlreadyUsedError,
    CaptchaExpiredError,
    CaptchaMaxAttemptsError,
)
from ..core.generator import ImageCaptchaGenerator
from ..core.validator import TokenValidator
from ..utils.randomizer import random_chars
from . import register_plugin

logger = logging.getLogger(__name__)


@register_plugin("image")
class ImageCaptcha(CaptchaBase):
    """A distorted-text CAPTCHA rendered as a PIL image.

    The image contains random characters drawn with variable fonts, rotations,
    and perspective warps on a noisy background, making automated OCR hard.

    Args:
        config:    :class:`~captcha_lib.config.CaptchaConfig` to use.
                   Defaults to the global default config.
        storage:   Optional :class:`~captcha_lib.core.base.StorageInterface`
                   backend.  If provided, token state is persisted there after
                   :meth:`generate`.

    Example::

        captcha = ImageCaptcha().generate()
        captcha.save("challenge.png")
        ok = captcha.verify(user_input)
    """

    def __init__(
        self,
        config: Optional[CaptchaConfig] = None,
        storage: Optional[Any] = None,
    ) -> None:
        cfg = config or get_default_config()
        super().__init__(cfg)
        self._storage = storage
        self._generator = ImageCaptchaGenerator(cfg)
        self._validator = TokenValidator(
            secret_key=cfg.secret_key,
            expiry_seconds=cfg.expiry_seconds,
            max_attempts=cfg.max_attempts,
            case_sensitive=cfg.case_sensitive,
        )
        self._image: Optional[Image] = None
        self._chars: str = ""
        self._attempt_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CaptchaBase interface
    # ------------------------------------------------------------------

    def generate(self) -> "ImageCaptcha":
        """Generate a new image CAPTCHA challenge.

        Populates :attr:`token`, :attr:`captcha_id`, and :attr:`answer_hash`.
        Stores token state via the configured storage backend (if any).

        Returns:
            *self* — for method chaining.
        """
        cfg = self._config
        self._chars = random_chars(cfg.length)
        self.captcha_id = secrets.token_hex(16)

        # Render image
        self._image = self._generator.generate(self._chars)

        # Issue signed token
        self.token = self._validator.issue_token(self._chars, self.captcha_id)

        # Persist to storage
        if self._storage is not None:
            self._storage.save(
                self.captcha_id,
                self.to_dict(),
                ttl=cfg.expiry_seconds,
            )

        logger.info("Generated image captcha: id=%s length=%d", self.captcha_id, cfg.length)
        return self

    def verify(self, answer: str) -> bool:
        """Verify the user's *answer* against this captcha.

        Args:
            answer: User-supplied answer text.

        Returns:
            ``True`` if correct.

        Raises:
            CaptchaExpiredError:     If the token has expired.
            CaptchaMaxAttemptsError: If the attempt limit is exceeded.
            CaptchaAlreadyUsedError: If the captcha was already solved.
            CaptchaInvalidError:     If the token is corrupt.
        """
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()

        result = self._validator.validate(
            self.token,
            answer,
            attempt_counter=self._attempt_counter,
        )

        if result:
            self.is_verified = True
            # Remove from storage (prevents replay via persisted state)
            if self._storage is not None:
                try:
                    self._storage.delete(self.captcha_id)
                except Exception:
                    pass

        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this captcha instance to a JSON-safe dictionary.

        Returns:
            Dictionary with token, id, type, attempts, and is_verified.
        """
        return {
            "captcha_type": "image",
            "captcha_id": self.captcha_id,
            "token": self.token,
            "attempts": self.attempts,
            "is_verified": self.is_verified,
            "length": self._config.length,
            "difficulty": self._config.difficulty.value,
        }

    def get_image(self) -> Optional[Image]:
        """Return the generated PIL Image.

        Returns:
            A :class:`PIL.Image.Image` object, or ``None`` if :meth:`generate`
            has not been called yet.
        """
        return self._image

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def bytes(self) -> bytes:
        """The CAPTCHA image as raw bytes in the configured output format.

        Returns:
            Image bytes (PNG by default).

        Raises:
            RuntimeError: If :meth:`generate` has not been called.
        """
        if self._image is None:
            raise RuntimeError("Call generate() before accessing .bytes")
        return self._image_to_bytes(self._config.output_format)

    def _image_to_bytes(self, fmt: OutputFormat) -> bytes:
        buf = io.BytesIO()
        save_kwargs: Dict[str, Any] = {}
        if fmt == OutputFormat.JPEG:
            save_kwargs["quality"] = 85
        self._image.save(buf, format=fmt.value, **save_kwargs)
        return buf.getvalue()

    def save(self, path: str, fmt: Optional[OutputFormat] = None) -> "ImageCaptcha":
        """Save the CAPTCHA image to disk.

        Args:
            path: File system path (extension used to infer format if *fmt*
                  is ``None`` and the path has a recognised extension).
            fmt:  Explicit :class:`~captcha_lib.config.OutputFormat`.  If
                  ``None``, the config's ``output_format`` is used.

        Returns:
            *self* — for method chaining.

        Raises:
            RuntimeError: If :meth:`generate` has not been called.
        """
        if self._image is None:
            raise RuntimeError("Call generate() before calling save()")

        effective_fmt = fmt or self._config.output_format
        self._image.save(path, format=effective_fmt.value)
        logger.info("Saved captcha image to %r", path)
        return self

    async def generate_async(self) -> "ImageCaptcha":
        """Async variant of :meth:`generate`.

        Delegates CPU-bound image rendering to a thread pool via
        :meth:`~captcha_lib.core.generator.ImageCaptchaGenerator.generate_async`.

        Returns:
            *self* — for method chaining.
        """
        cfg = self._config
        self._chars = random_chars(cfg.length)
        self.captcha_id = secrets.token_hex(16)

        self._image = await self._generator.generate_async(self._chars)
        self.token = self._validator.issue_token(self._chars, self.captcha_id)

        if self._storage is not None:
            self._storage.save(self.captcha_id, self.to_dict(), ttl=cfg.expiry_seconds)

        return self

    def show(self) -> "ImageCaptcha":
        """Open the captcha image in the system viewer (dev/debug helper).

        Returns:
            *self* — for method chaining.
        """
        if self._image is None:
            raise RuntimeError("Call generate() before show()")
        self._image.show()
        return self
