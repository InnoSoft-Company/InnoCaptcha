# How to Add a New Captcha Type

Adding a new captcha type requires **one file** and **one decorator** — no core code changes needed.

---

## The 4 Steps

### Step 1 — Create your file in `types/`

```
V3/types/my_captcha.py
```

### Step 2 — Write your class

```python
# V3/types/my_captcha.py

import secrets
from typing import Any, Dict, Optional

from captcha_lib.types import register_plugin
from captcha_lib.core.base import CaptchaBase
from captcha_lib.core.exceptions import CaptchaAlreadyUsedError
from captcha_lib.core.validator import TokenValidator
from captcha_lib.config import CaptchaConfig, get_default_config


@register_plugin("my_type")   # choose a unique name
class MyCaptcha(CaptchaBase):

    def __init__(self, config: Optional[CaptchaConfig] = None, storage=None):
        super().__init__(config or get_default_config())
        self._storage = storage
        self._validator = TokenValidator(
            expiry_seconds=self._config.expiry_seconds,
            max_attempts=self._config.max_attempts,
        )
        self._answer: str = ""
        self._attempt_counter: Dict[str, int] = {}

    # REQUIRED: generate the challenge
    def generate(self) -> "MyCaptcha":
        self._answer = "..."          # whatever your challenge produces
        self.captcha_id = secrets.token_hex(16)
        self.token = self._validator.issue_token(self._answer, self.captcha_id)
        if self._storage:
            self._storage.save(self.captcha_id, self.to_dict(), ttl=self._config.expiry_seconds)
        return self

    # REQUIRED: verify user input
    def verify(self, answer: str) -> bool:
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()
        result = self._validator.validate(self.token, answer.strip(), self._attempt_counter)
        if result:
            self.is_verified = True
        return result

    # REQUIRED: serialise state
    def to_dict(self) -> Dict[str, Any]:
        return {
            "captcha_type": "my_type",
            "captcha_id": self.captcha_id,
            "token": self.token,
            "attempts": self.attempts,
            "is_verified": self.is_verified,
        }

    # REQUIRED: return PIL.Image or None
    def get_image(self):
        return None
```

### Step 3 — Register it in `types/__init__.py`

Add your module to `_BUILTIN_MODULES` so it is auto-imported:

```python
# V3/types/__init__.py
_BUILTIN_MODULES = [
    "captcha_lib.types.image",
    "captcha_lib.types.math",
    "captcha_lib.types.my_captcha",   # <-- add this line
]
```

### Step 4 — Use it

```python
from captcha_lib import Captcha

captcha = Captcha.create(captcha_type="my_type")
ok = captcha.verify(user_input)
```

---

## Concrete Example — Colour Captcha

```python
@register_plugin("color")
class ColorCaptcha(CaptchaBase):
    _COLORS = {"red": (220,50,50), "blue": (50,100,220), "green": (50,180,80)}

    def generate(self):
        from PIL.Image import new as mkimg
        self._color_name = secrets.choice(list(self._COLORS))
        rgb = self._COLORS[self._color_name]
        self._image = mkimg("RGB", (self._config.width, self._config.height), rgb)
        self.captcha_id = secrets.token_hex(16)
        self.token = self._validator.issue_token(self._color_name, self.captcha_id)
        return self

    def get_image(self):
        return self._image

    def verify(self, answer: str) -> bool:
        self.attempts += 1
        if self.is_verified:
            raise CaptchaAlreadyUsedError()
        result = self._validator.validate(self.token, answer.strip(), self._attempt_counter)
        if result:
            self.is_verified = True
        return result

    def to_dict(self):
        return {"captcha_type": "color", "captcha_id": self.captcha_id,
                "token": self.token, "attempts": self.attempts, "is_verified": self.is_verified}
```

---

## What You Need vs. What You Don't

| What you change | Required? |
|----------------|-----------|
| New file `types/your_type.py` | ✅ Yes |
| `@register_plugin("name")` decorator | ✅ Yes |
| Implement `generate`, `verify`, `to_dict`, `get_image` | ✅ Yes |
| Add to `_BUILTIN_MODULES` in `types/__init__.py` | Only for auto-loading |
| Touch any core file | ❌ Never |

---

## See Also

- [`types/example_plugin.py`](../types/example_plugin.py) — fully-commented `AudioCaptcha` stub template
- [`types/image.py`](../types/image.py) — complete real-world example (image text captcha)
- [`types/math.py`](../types/math.py) — complete real-world example (math captcha)
- [`core/base.py`](../core/base.py) — `CaptchaBase` ABC definition
