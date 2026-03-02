"""
examples/basic_usage.py
~~~~~~~~~~~~~~~~~~~~~~~~
Demonstrates the simple, everyday API of captcha-lib.

Run from the V3 directory::

    python examples/basic_usage.py
"""

import sys
import os

# Allow running directly from the V3 directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from captcha_lib import Captcha, CaptchaConfig, DifficultyLevel
from captcha_lib.core.exceptions import (
    CaptchaExpiredError,
    CaptchaInvalidError,
    CaptchaMaxAttemptsError,
)
from captcha_lib.storage import MemoryStorage

# ---------------------------------------------------------------------------
# 1. Simplest possible usage
# ---------------------------------------------------------------------------
print("=== 1. Simple image captcha ===")
captcha = Captcha.create()  # default: image, medium difficulty
captcha.save("output_simple.png")
print(f"  Token:      {captcha.token}")
print(f"  Captcha ID: {captcha.captcha_id}")
print(f"  Saved to:   output_simple.png")

# Verify with a wrong answer (returns False)
ok = captcha.verify("wrong")
print(f"  Wrong answer → {ok}")

# ---------------------------------------------------------------------------
# 2. Math captcha
# ---------------------------------------------------------------------------
print("\n=== 2. Math captcha ===")
math_captcha = Captcha.create(captcha_type="math")
math_captcha.save("output_math.png")
math_captcha.verify("11")  # e.g. correct answer to "7 + 4 = ?"
print(f"  Problem: {math_captcha.problem}")          # e.g. "7 + 4 = ?"
print(f"  Token:   {math_captcha.token}")
print(f"  Saved to: output_math.png")

# ---------------------------------------------------------------------------
# 3. Hard difficulty, 8 chars
# ---------------------------------------------------------------------------
print("\n=== 3. Hard difficulty, custom config ===")
config = CaptchaConfig(difficulty=DifficultyLevel.HARD, length=8, width=220, height=70)
hard_captcha = Captcha.create(config=config)
hard_captcha.save("output_hard.png")
print(f"  Length:     {config.length}")
print(f"  Difficulty: {config.difficulty.value}")
print(f"  Saved to:   output_hard.png")

# ---------------------------------------------------------------------------
# 4. Raw bytes (for web responses)
# ---------------------------------------------------------------------------
print("\n=== 4. Get raw PNG bytes ===")
captcha_bytes = Captcha.create()
img_bytes = captcha_bytes.bytes
print(f"  Image bytes: {len(img_bytes)} bytes (PNG)")

# ---------------------------------------------------------------------------
# 5. Custom storage backend
# ---------------------------------------------------------------------------
print("\n=== 5. Custom MemoryStorage ===")
store = MemoryStorage(max_size=500)
captcha_stored = Captcha.create(storage=store)
print(f"  Storage entries: {len(store)}")
print(f"  ID in store:     {store.exists(captcha_stored.captcha_id)}")

# ---------------------------------------------------------------------------
# 6. Error handling
# ---------------------------------------------------------------------------
print("\n=== 6. Error handling ===")
limited = Captcha.create(config=CaptchaConfig(max_attempts=2))
limited.verify("bad1")
limited.verify("bad2")
try:
    limited.verify("bad3")
except CaptchaMaxAttemptsError as e:
    print(f"  Caught: {e}")

# ---------------------------------------------------------------------------
# 7. List available plugins
# ---------------------------------------------------------------------------
print("\n=== 7. Registered plugins ===")
print(f"  Plugins: {Captcha.plugins()}")

print("\n✅  All examples ran successfully.")
