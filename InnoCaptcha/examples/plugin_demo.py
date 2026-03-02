"""
examples/plugin_demo.py
~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrates the captcha-lib plugin / extension system.

Shows how to:
1. Create a custom captcha type
2. Register it with the plugin registry
3. Use it through the standard Captcha.create() factory
4. Inspect the plugin registry

Run from the V3 directory::

    python examples/plugin_demo.py
"""

import sys
import os
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captcha_lib import Captcha, register_plugin
from captcha_lib.config import CaptchaConfig, get_default_config
from captcha_lib.core.base import CaptchaBase
from captcha_lib.core.exceptions import CaptchaAlreadyUsedError
from captcha_lib.core.validator import TokenValidator


# ---------------------------------------------------------------------------
# Step 1 — Define your custom captcha class
# ---------------------------------------------------------------------------

@register_plugin("emoji")          # <-- This is all you need to integrate!
class EmojiCaptcha(CaptchaBase):
    """A fun emoji-sequence CAPTCHA.

    The user is shown a sequence of emoji and asked to reproduce it.
    (Rendered as text for this demo — a real implementation would use
    an emoji-capable font.)
    """

    _EMOJI_POOL = ["🐶", "🐱", "🐸", "🦊", "🐼", "🐨", "🦁", "🐯",
                   "🦄", "🐙", "🦋", "🌸", "⭐", "🍕", "🚀", "🎯"]

    def __init__(
        self,
        config: CaptchaConfig | None = None,
        storage=None,
    ) -> None:
        cfg = config or get_default_config()
        super().__init__(cfg)
        self._storage = storage
        self._sequence: list[str] = []
        self._validator = TokenValidator(
            secret_key=cfg.secret_key,
            expiry_seconds=cfg.expiry_seconds,
            max_attempts=cfg.max_attempts,
            case_sensitive=True,
        )
        self._attempt_counter: dict[str, int] = {}

    def generate(self) -> "EmojiCaptcha":
        """Pick a random emoji sequence and issue a token."""
        cfg = self._config
        self._sequence = [secrets.choice(self._EMOJI_POOL) for _ in range(cfg.length or 4)]
        answer = "".join(self._sequence)
        self.captcha_id = secrets.token_hex(16)
        self.token = self._validator.issue_token(answer, self.captcha_id)
        print(f"  [EmojiCaptcha] Challenge: {'  '.join(self._sequence)}")
        return self

    def verify(self, answer: str) -> bool:
        """Verify the user's emoji sequence."""
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()
        result = self._validator.validate(
            self.token, answer, attempt_counter=self._attempt_counter
        )
        if result:
            self.is_verified = True
        return result

    def to_dict(self) -> dict:
        return {
            "captcha_type": "emoji",
            "captcha_id": self.captcha_id,
            "token": self.token,
            "attempts": self.attempts,
            "is_verified": self.is_verified,
        }

    def get_image(self):
        """Emoji captcha has no image in this demo."""
        return None

    @property
    def answer(self) -> str:
        """The correct answer (for demo purposes — don't expose in production!)."""
        return "".join(self._sequence)


# ---------------------------------------------------------------------------
# Step 2 — Use it through the standard factory
# ---------------------------------------------------------------------------

print("=== Emoji Captcha Plugin Demo ===\n")

print("Available plugins (after registration):")
print(" ", Captcha.plugins())

print("\n--- Generating emoji captcha ---")
captcha = Captcha.create(captcha_type="emoji", config=CaptchaConfig(length=4))

correct_answer = captcha.answer

# Simulate a wrong answer
wrong = captcha.verify("🐶🐶🐶🐶")
print(f"  Wrong answer → {wrong}")

# Simulate the correct answer
right = captcha.verify(correct_answer)
print(f"  Correct answer → {right}")
print(f"  Verified: {captcha.is_verified}")

# ---------------------------------------------------------------------------
# Step 3 — Dynamic plugin loading from external file
# ---------------------------------------------------------------------------

print("\n--- Observer/logging pattern via subclassing ---")

@register_plugin("logged_image", overwrite=True)
class LoggedImageCaptcha(Captcha.plugins().__class__):  # type: ignore
    pass

# Show the underlying class directly for simplicity
from captcha_lib.types import get_plugin
ImagePlugin = get_plugin("image")

class LoggedImageCaptchaFull(ImagePlugin):
    """Image captcha that logs every verification attempt."""

    def verify(self, answer: str) -> bool:
        print(f"  [Observer] Verifying attempt #{self.attempts + 1} for id={self.captcha_id[:8]}…")
        result = super().verify(answer)
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  [Observer] Result: {status}")
        return result

print("\n--- Logged image captcha ---")
logged = LoggedImageCaptchaFull().generate()
logged.verify("bad_answer")
print()

print("✅  Plugin demo complete.")
