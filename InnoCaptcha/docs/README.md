# captcha-lib

> A professional, pluggable, production-ready CAPTCHA library for Python.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Features

- 🔌 **Pluggable architecture** — add any captcha type without touching core code
- 🖼️ **Image text CAPTCHA** — distorted text, variable fonts, flexible noise
- ➕ **Math CAPTCHA** — arithmetic challenges rendered as images
- 🔐 **HMAC-signed tokens** — no plaintext answers stored; expiry + replay protection  
- 💾 **Swappable storage** — in-memory (default) or Redis
- ⚡ **Async support** — `generate_async()` via `asyncio.to_thread`
- 🎚️ **Difficulty levels** — `easy`, `medium`, `hard` presets
- 🧵 **Thread-safe** — font cache and storage use `threading.Lock`
- 📦 **pip installable** — minimal dependencies (only Pillow required)

---

## Installation

```bash
# Core
pip install captcha-lib

# With Redis storage support
pip install "captcha-lib[redis]"

# For development
pip install "captcha-lib[dev]"
```

> **Font**: The library ships with `DroidSansMono.ttf` in the `data/` directory.
> Custom fonts can be passed via `CaptchaConfig(fonts=["/path/to/font.ttf"])`.

---

## Quick Start

```python
from captcha_lib import Captcha

# Create a captcha (image type, medium difficulty by default)
captcha = Captcha.create()

# Save to file
captcha.save("challenge.png")

# Get raw bytes (for HTTP responses, e.g. Flask/Django)
img_bytes = captcha.bytes   # PNG bytes

# Validate the user's answer
is_correct = captcha.verify(user_input)   # True / False
```

---

## API Reference

### `Captcha.create()`

```python
Captcha.create(
    config: CaptchaConfig | None = None,
    storage: StorageInterface | None = None,
    captcha_type: str | None = None,    # "image" | "math" | your_plugin
) -> CaptchaBase
```

Returns a **fully generated** captcha instance with `.token` populated.

### `CaptchaConfig`

```python
from captcha_lib import CaptchaConfig, DifficultyLevel

cfg = CaptchaConfig(
    captcha_type="image",              # plugin name
    difficulty=DifficultyLevel.HARD,   # EASY | MEDIUM | HARD
    length=8,                          # number of characters
    width=220, height=70,              # image dimensions in px
    expiry_seconds=300,                # token TTL
    max_attempts=3,                    # max wrong answers
    case_sensitive=False,
    fonts=["/path/to/custom.ttf"],     # custom fonts (optional)
    secret_key="my-secret",            # HMAC key (auto-generated if None)
)

# Convenience constructors
cfg = CaptchaConfig.easy()
cfg = CaptchaConfig.medium(length=6)
cfg = CaptchaConfig.hard(width=240)
```

### Difficulty Presets

| Level  | Length | Noise Dots | Rotation    | Warp    |
|--------|--------|------------|-------------|---------|
| easy   | 4      | 15         | ±15°        | minimal |
| medium | 6      | 30         | ±30°        | moderate|
| hard   | 8      | 50         | ±45°        | heavy   |

---

## Captcha Types

### Image Captcha (default)

```python
captcha = Captcha.create()                       # or:
captcha = Captcha.image(difficulty="hard")       # shortcut

captcha.save("out.png")
captcha.verify(user_answer)                      # True / False
token = captcha.token                            # signed JWT-style token
img   = captcha.get_image()                     # PIL.Image
```

### Math Captcha

```python
captcha = Captcha.create(captcha_type="math")   # or:
captcha = Captcha.math()                         # shortcut

print(captcha.problem)   # e.g. "7 + 4 = ?"
captcha.save("math.png")
captcha.verify("11")     # True
```

### Async Usage

```python
import asyncio
from captcha_lib import Captcha

async def generate():
    captcha = await Captcha.create_async()
    # ... rest of your async handler
    return captcha.bytes

asyncio.run(generate())
```

---

## Storage Backends

### In-Memory (default)

```python
from captcha_lib.storage import MemoryStorage

store = MemoryStorage(max_size=1000)   # LRU eviction when full
captcha = Captcha.create(storage=store)
```

### Redis

```bash
pip install "captcha-lib[redis]"
```

```python
import redis
from captcha_lib.storage import RedisStorage

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
store = RedisStorage(r, key_prefix="myapp:captcha:")
captcha = Captcha.create(storage=store)
```

### Set a Global Default Storage

```python
from captcha_lib import set_default_storage
from captcha_lib.storage import MemoryStorage

set_default_storage(MemoryStorage(max_size=5000))
# All subsequent Captcha.create() calls use this store
```

---

## Plugin System

Add a new captcha type in **four steps**, without touching any library code:

```python
# my_audio_captcha.py
from captcha_lib.types import register_plugin
from captcha_lib.core import CaptchaBase
from captcha_lib.config import get_default_config
from captcha_lib.core.validator import TokenValidator
from captcha_lib.core.exceptions import CaptchaAlreadyUsedError
import secrets

@register_plugin("audio")   # <-- one decorator to register
class AudioCaptcha(CaptchaBase):

    def __init__(self, config=None, storage=None):
        super().__init__(config or get_default_config())
        self._validator = TokenValidator(
            expiry_seconds=self._config.expiry_seconds,
            max_attempts=self._config.max_attempts,
        )
        self._chars = ""
        self._attempt_counter = {}

    def generate(self):
        self._chars = secrets.token_hex(3).upper()[:self._config.length]
        self.captcha_id = secrets.token_hex(16)
        self.token = self._validator.issue_token(self._chars, self.captcha_id)
        # TODO: synthesise audio from self._chars
        return self

    def verify(self, answer: str) -> bool:
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()
        result = self._validator.validate(self.token, answer, self._attempt_counter)
        if result:
            self.is_verified = True
        return result

    def to_dict(self):
        return {"captcha_type": "audio", "token": self.token, ...}

    def get_image(self):
        return None  # no image for audio type
```

Then use it through the standard factory:

```python
import my_audio_captcha  # imports trigger @register_plugin

from captcha_lib import Captcha
captcha = Captcha.create(captcha_type="audio")
```

See [`types/example_plugin.py`](types/example_plugin.py) for a fully-documented template.

---

## Error Handling

```python
from captcha_lib.core import (
    CaptchaExpiredError,
    CaptchaInvalidError,
    CaptchaMaxAttemptsError,
    CaptchaAlreadyUsedError,
)

try:
    is_ok = captcha.verify(user_answer)
except CaptchaExpiredError:
    # Token TTL elapsed — issue a new captcha
    captcha = Captcha.create()
except CaptchaMaxAttemptsError as e:
    # Too many wrong guesses
    print(f"Locked after {e.max_attempts} attempts")
except CaptchaAlreadyUsedError:
    # Replay attack — token already consumed
    pass
```

---

## Security Model

| Feature | Implementation |
|---------|---------------|
| Answer storage | SHA-256 hash only — plaintext never stored |
| Token signing | HMAC-SHA256 with configurable secret key |
| Expiry | Unix timestamp baked into token; checked on every verify() |
| Replay prevention | Successful token IDs added to an in-memory deny-set |
| Attempt limiting | Per-captcha counter; raises after `max_attempts` |
| Randomness | Python `secrets` module throughout |

---

## Project Structure

```
V3/
├── __init__.py          # Public API — Captcha factory + re-exports
├── config.py            # CaptchaConfig dataclass, DifficultyLevel enum
├── setup.py             # pip install configuration
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── base.py          # CaptchaBase, StorageInterface (ABCs)
│   ├── generator.py     # ImageCaptchaGenerator (sync + async)
│   ├── validator.py     # TokenValidator (HMAC, expiry, replay)
│   └── exceptions.py   # Full exception hierarchy
├── types/
│   ├── __init__.py      # Plugin registry (register_plugin, get_plugin, list_plugins)
│   ├── image.py         # ImageCaptcha plugin
│   ├── math.py          # MathCaptcha plugin
│   └── example_plugin.py  # AudioCaptcha stub / template
├── storage/
│   ├── __init__.py
│   ├── memory.py        # MemoryStorage (thread-safe, LRU, TTL)
│   └── redis.py         # RedisStorage (optional)
├── utils/
│   ├── __init__.py
│   ├── randomizer.py    # secrets-based random helpers
│   ├── hashing.py       # HMAC sign/verify, answer hashing
│   └── image_utils.py   # PIL rendering (draw_character, create_captcha_image)
├── data/
│   └── DroidSansMono.ttf
└── examples/
    ├── basic_usage.py
    └── plugin_demo.py
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
