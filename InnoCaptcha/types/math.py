"""
captcha_lib.types.math
~~~~~~~~~~~~~~~~~~~~~~~
Math CAPTCHA plugin — generates an arithmetic challenge rendered as an image.

The answer is the numeric result of the equation; users type a number.

Registered under the key ``"math"`` in the plugin registry.
"""

from __future__ import annotations

import io
import logging
import secrets
from typing import Any, Dict, Optional

from PIL.Image import Image

from ..config import CaptchaConfig, OutputFormat, get_default_config
from ..core.base import CaptchaBase
from ..core.exceptions import CaptchaAlreadyUsedError
from ..core.generator import ImageCaptchaGenerator
from ..core.validator import TokenValidator
from ..utils.randomizer import random_math_problem
from . import register_plugin

logger = logging.getLogger(__name__)


@register_plugin("math")
class MathCaptcha(CaptchaBase):
    """An arithmetic-challenge CAPTCHA rendered as a PIL image.

    The user is shown an equation like ``"7 + 4 = ?"`` and must type the
    numeric answer.  Difficulty controls the range of operands and allowed
    operations.

    Args:
        config:  :class:`~captcha_lib.config.CaptchaConfig`.
        storage: Optional storage backend.

    Example::

        captcha = MathCaptcha().generate()
        captcha.save("math_challenge.png")
        ok = captcha.verify("11")
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
            case_sensitive=False,
        )
        self._image: Optional[Image] = None
        self._problem: str = ""
        self._answer: int = 0
        self._attempt_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------
    # CaptchaBase interface
    # ------------------------------------------------------------------

    def generate(self) -> "MathCaptcha":
        """Generate a math CAPTCHA challenge.

        Returns:
            *self* — for method chaining.
        """
        cfg = self._config
        difficulty_str = cfg.difficulty.value
        self._problem, self._answer = random_math_problem(difficulty_str)
        self.captcha_id = secrets.token_hex(16)

        # The rendered string shows the equation; answer is numeric
        display_text = f"{self._problem} = ?"
        self._image = self._generator.generate(display_text)

        # Issue token against the string answer
        self.token = self._validator.issue_token(str(self._answer), self.captcha_id)

        if self._storage is not None:
            self._storage.save(self.captcha_id, self.to_dict(), ttl=cfg.expiry_seconds)

        logger.info(
            "Generated math captcha: id=%s problem=%r answer=%d",
            self.captcha_id, self._problem, self._answer,
        )
        return self

    def verify(self, answer: str) -> bool:
        """Verify the user's numeric *answer*.

        Args:
            answer: User-supplied number string (e.g. ``"11"``).

        Returns:
            ``True`` if the answer is correct.

        Raises:
            CaptchaAlreadyUsedError: If already verified.
            CaptchaExpiredError:     If expired.
            CaptchaMaxAttemptsError: If attempt limit exceeded.
        """
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()

        # Normalise answer — strip whitespace, allow "11" or " 11 "
        normalised = answer.strip()

        result = self._validator.validate(
            self.token,
            normalised,
            attempt_counter=self._attempt_counter,
        )

        if result:
            self.is_verified = True
            if self._storage is not None:
                try:
                    self._storage.delete(self.captcha_id)
                except Exception:
                    pass
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialise this instance to a JSON-safe dictionary.

        Returns:
            Dictionary representation of the math captcha.
        """
        return {
            "captcha_type": "math",
            "captcha_id": self.captcha_id,
            "token": self.token,
            "attempts": self.attempts,
            "is_verified": self.is_verified,
            "difficulty": self._config.difficulty.value,
            # Note: problem string omitted in production to prevent spoilers;
            # include it here for debugging.  Remove in strict implementations.
            "problem": self._problem,
        }

    def get_image(self) -> Optional[Image]:
        """Return the rendered math equation image.

        Returns:
            A :class:`PIL.Image.Image`, or ``None`` before :meth:`generate`.
        """
        return self._image

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @property
    def problem(self) -> str:
        """The displayed equation string, e.g. ``"7 + 4 = ?"``."""
        return f"{self._problem} = ?"

    @property
    def bytes(self) -> bytes:
        """The challenge image as raw PNG bytes."""
        if self._image is None:
            raise RuntimeError("Call generate() before accessing .bytes")
        buf = io.BytesIO()
        self._image.save(buf, format=self._config.output_format.value)
        return buf.getvalue()

    def save(self, path: str, fmt: Optional[OutputFormat] = None) -> "MathCaptcha":
        """Save the challenge image to *path*.

        Args:
            path: File system destination.
            fmt:  Override output format.

        Returns:
            *self* — for method chaining.
        """
        if self._image is None:
            raise RuntimeError("Call generate() before calling save()")
        effective_fmt = fmt or self._config.output_format
        self._image.save(path, format=effective_fmt.value)
        logger.info("Saved math captcha image to %r", path)
        return self

    async def generate_async(self) -> "MathCaptcha":
        """Async variant of :meth:`generate`.

        Returns:
            *self* — for method chaining.
        """
        cfg = self._config
        self._problem, self._answer = random_math_problem(cfg.difficulty.value)
        self.captcha_id = secrets.token_hex(16)

        display_text = f"{self._problem} = ?"
        self._image = await self._generator.generate_async(display_text)
        self.token = self._validator.issue_token(str(self._answer), self.captcha_id)

        if self._storage is not None:
            self._storage.save(self.captcha_id, self.to_dict(), ttl=cfg.expiry_seconds)

        return self
