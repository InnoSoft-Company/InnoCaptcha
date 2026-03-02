"""
captcha_lib.types.example_plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Template / stub for third-party captcha type plugins.

Copy this file, implement the required methods, and register your class
with :func:`~captcha_lib.types.register_plugin`.

This file ships as an "audio" stub that demonstrates the full contract
without actually generating audio (since that requires additional system
dependencies).  It is *not* registered by default.

Usage::

    # my_package/audio_captcha.py
    from captcha_lib.types import register_plugin
    from captcha_lib.core import CaptchaBase

    @register_plugin("audio")
    class AudioCaptcha(CaptchaBase):
        def generate(self): ...
        def verify(self, answer): ...
        def to_dict(self): ...
        def get_image(self): return None
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Dict, Optional

from ..config import CaptchaConfig, get_default_config
from ..core.base import CaptchaBase
from ..core.exceptions import CaptchaAlreadyUsedError
from ..core.validator import TokenValidator
from ..utils.randomizer import random_chars

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NOTE: Uncomment the decorator to register this plugin automatically.
#       Leave it commented out if you only want to use it manually.
# ---------------------------------------------------------------------------
# from . import register_plugin
# @register_plugin("audio")


class AudioCaptcha(CaptchaBase):
    """Stub audio CAPTCHA — a template illustrating the plugin contract.

    To create a real audio captcha:
    1. Generate a random character sequence.
    2. Synthesise audio (e.g. via ``gtts``, ``pyttsx3``, or pre-recorded clips).
    3. Issue a token via :class:`~captcha_lib.core.validator.TokenValidator`.
    4. Return audio bytes from a ``get_audio()`` method (not required by base).
    5. Implement :meth:`verify` to check the user transcription.
    6. Decorate with ``@register_plugin("audio")``.

    Args:
        config:  Configuration object.
        storage: Optional storage backend.
    """

    # ------------------------------------------------------------------ #
    # Step 1: Initialise your plugin, inject dependencies & set defaults  #
    # ------------------------------------------------------------------ #
    def __init__(
        self,
        config: Optional[CaptchaConfig] = None,
        storage: Optional[Any] = None,
    ) -> None:
        cfg = config or get_default_config()
        super().__init__(cfg)
        self._storage = storage
        self._validator = TokenValidator(
            secret_key=cfg.secret_key,
            expiry_seconds=cfg.expiry_seconds,
            max_attempts=cfg.max_attempts,
            case_sensitive=False,
        )
        self._chars: str = ""
        self._audio_bytes: Optional[bytes] = None
        self._attempt_counter: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Step 2: Implement generate() — create the challenge material        #
    # ------------------------------------------------------------------ #
    def generate(self) -> "AudioCaptcha":
        """Generate the audio captcha challenge.

        Replace the stub below with real audio synthesis.

        Returns:
            *self* — for method chaining.
        """
        cfg = self._config
        self._chars = random_chars(cfg.length)
        self.captcha_id = secrets.token_hex(16)

        # --- TODO: synthesise audio from self._chars ---
        # Example using gTTS:
        #   from gtts import gTTS
        #   import io
        #   tts = gTTS(text=" ".join(self._chars), lang="en", slow=True)
        #   buf = io.BytesIO()
        #   tts.write_to_fp(buf)
        #   self._audio_bytes = buf.getvalue()

        # Stub: just store None
        self._audio_bytes = None

        self.token = self._validator.issue_token(self._chars, self.captcha_id)

        if self._storage is not None:
            self._storage.save(self.captcha_id, self.to_dict(), ttl=cfg.expiry_seconds)

        logger.info("Generated audio captcha stub: id=%s", self.captcha_id)
        return self

    # ------------------------------------------------------------------ #
    # Step 3: Implement verify() — validate the user's response           #
    # ------------------------------------------------------------------ #
    def verify(self, answer: str) -> bool:
        """Verify the user's transcription of the audio.

        Args:
            answer: User-supplied transcription string.

        Returns:
            ``True`` if the answer matches.

        Raises:
            CaptchaAlreadyUsedError: If already solved.
            CaptchaExpiredError:     If the token has expired.
            CaptchaMaxAttemptsError: If too many attempts.
        """
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()

        result = self._validator.validate(
            self.token,
            answer.strip(),
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

    # ------------------------------------------------------------------ #
    # Step 4: Implement to_dict() — serialise state for storage / API     #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe representation of this captcha instance.

        Returns:
            Dictionary with captcha metadata.
        """
        return {
            "captcha_type": "audio",
            "captcha_id": self.captcha_id,
            "token": self.token,
            "attempts": self.attempts,
            "is_verified": self.is_verified,
            "difficulty": self._config.difficulty.value,
        }

    # ------------------------------------------------------------------ #
    # Step 5: Implement get_image() — return None for non-image types     #
    # ------------------------------------------------------------------ #
    def get_image(self) -> None:
        """Audio captcha has no image component.

        Returns:
            Always ``None``.
        """
        return None

    # ------------------------------------------------------------------ #
    # Step 6: Add any additional helpers your type needs                  #
    # ------------------------------------------------------------------ #
    def get_audio(self) -> Optional[bytes]:
        """Return the generated audio bytes (MP3).

        Returns:
            Raw audio bytes, or ``None`` if not yet generated.
        """
        return self._audio_bytes
