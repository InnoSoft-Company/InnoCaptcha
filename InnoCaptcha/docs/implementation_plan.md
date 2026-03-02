# CAPTCHA Library – Full Professional Refactoring

Refactor the single-file [image.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py) CAPTCHA library into a modular, production-ready Python package with a plugin registry, multiple storage backends, HMAC-based security, configurable difficulty, and a clean public API.

## Proposed Changes

---

### Core Package Infrastructure

#### [MODIFY] [\_\_init\_\_.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/__init__.py) *(new file)*
- `Captcha` factory class with [create()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#86-96) classmethod
- Re-exports: `CaptchaBase`, `register_plugin`, `CaptchaConfig`, storage classes
- Clean public API surface

#### [NEW] [config.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py)
- `CaptchaConfig` dataclass (difficulty, length, width, height, expiry, max_attempts, fonts, font_sizes)
- `DifficultyLevel` enum: `EASY`, `MEDIUM`, `HARD`
- Singleton accessor `get_default_config()` / `set_default_config()`

---

### Core Module (`core/`)

#### [NEW] [base.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/base.py)
- `CaptchaBase` — ABC with abstract: `generate()`, `verify(answer)`, `to_dict()`, `get_image()` 
- `StorageInterface` — ABC with: `save()`, `load()`, `delete()`, `exists()`

#### [NEW] [exceptions.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/exceptions.py)
- `CaptchaError` (base)
- `CaptchaExpiredError`, `CaptchaInvalidError`, `CaptchaMaxAttemptsError`
- `StorageError`, `PluginNotFoundError`, `RateLimitError`

#### [NEW] [generator.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/generator.py)
- `ImageCaptchaGenerator` orchestration class
- Calls into `utils/image_utils.py` for actual rendering
- Supports async generation via `asyncio.to_thread`

#### [NEW] [validator.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/validator.py)
- `TokenValidator` class
- `create_token(answer, config)` — HMAC-signed JWT-style token with expiry
- `validate_token(token, answer)` — verify signature + expiry + attempt count
- Replay protection via token invalidation after successful verification

---

### Utilities (`utils/`)

#### [NEW] [randomizer.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/randomizer.py)
- [random_float()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#69-72), [random_color()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#188-196), `random_chars()`, `random_math_problem()`
- All using `secrets` module for cryptographic-quality randomness

#### [NEW] [hashing.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/hashing.py)
- `generate_secret_key()` — `secrets.token_hex(32)`
- `hmac_sign(data, key)` / `hmac_verify(data, signature, key)`
- `hash_answer(answer)` — SHA-256 for case-insensitive comparison

#### [NEW] [image_utils.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/image_utils.py)
- All image logic extracted from original [image.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py):
  - [draw_character()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#97-143), [create_captcha_image()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#144-187)
  - [create_noise_curve()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#73-85), [create_noise_dots()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#86-96)
  - [get_truefonts()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#41-63) with thread-safe `threading.Lock` cache

---

### CAPTCHA Types (`types/`)

#### [NEW] [\_\_init\_\_.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py)
- `_registry: Dict[str, Type[CaptchaBase]]` plugin registry
- `register_plugin(name)` decorator
- `get_plugin(name)` lookup
- `list_plugins()` introspection

#### [NEW] [image.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/image.py)
- `ImageCaptcha(CaptchaBase)` — refactored from original
- Calls `core/generator.py` → `utils/image_utils.py`
- `get_image()` returns `PIL.Image`, `to_bytes(fmt)` for PNG/JPEG output
- `save(path)` convenience method
- Registered as `@register_plugin("image")`

#### [NEW] [math.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/math.py)
- `MathCaptcha(CaptchaBase)` — arithmetic challenge rendered as image
- Operations: +, -, × depending on difficulty
- Registered as `@register_plugin("math")`

#### [NEW] [example\_plugin.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/example_plugin.py)
- `AudioCaptcha(CaptchaBase)` stub — fully documented template for new plugin authors
- Comments explaining every hook

---

### Storage Backends (`storage/`)

#### [NEW] [memory.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/memory.py)
- `MemoryStorage(StorageInterface)` — `threading.Lock`-protected `dict`
- TTL-based expiry cleanup on `load()`

#### [NEW] [redis.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/redis.py)
- `RedisStorage(StorageInterface)` — wraps `redis.Redis` (optional dep)
- Uses Redis TTL natively; graceful `ImportError` if redis not installed

---

### Package Metadata

#### [NEW] [setup.py](file:///d:/VS%20code/Python-Projects/text%20captcha/setup.py)
- `setuptools` config: name, version, author, classifiers, install_requires, extras_require (redis)

#### [MODIFY] [requirements.txt](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/requirements.txt)
- `Pillow>=10.0.0`, `cryptography>=40.0.0`; optional `redis>=4.0.0`

#### [NEW] [README.md](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/README.md)
- Full installation guide, quick-start, plugin authoring guide, API reference

#### [NEW] [examples/basic\_usage.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/examples/basic_usage.py)
#### [NEW] [examples/plugin\_demo.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/examples/plugin_demo.py)

---

## Verification Plan

### Automated Tests
Run the following command from `d:\VS code\Python-Projects\text captcha\V3\`:

```bash
python -c "
import sys, os
sys.path.insert(0, '.')

# 1. Import chain
from __init__ import Captcha, CaptchaConfig, DifficultyLevel
from core.base import CaptchaBase, StorageInterface
from core.exceptions import CaptchaExpiredError, CaptchaInvalidError
from types import list_plugins, get_plugin
from storage.memory import MemoryStorage
from utils.hashing import hmac_sign, hmac_verify, hash_answer
from utils.randomizer import random_color, random_chars

# 2. Plugin registry
plugins = list_plugins()
assert 'image' in plugins and 'math' in plugins, f'Missing plugins: {plugins}'

# 3. Image CAPTCHA full cycle
captcha = Captcha.create()
assert captcha.token is not None
assert len(captcha.bytes) > 0
result = captcha.verify('wrong')
assert result == False
print('All checks passed')
"
```

### Manual Verification
1. Run `python examples/basic_usage.py` — should save `output.png` and print token
2. Open `output.png` to visually verify CAPTCHA image renders correctly
3. Run `python examples/plugin_demo.py` — should demonstrate custom plugin registration
