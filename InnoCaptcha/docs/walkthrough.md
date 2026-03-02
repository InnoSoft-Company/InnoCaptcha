# CAPTCHA Library Refactoring — Walkthrough

## What Was Accomplished

A complete, professional refactoring of the original single-file [image.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py) into a **fully-modular, pip-installable Python package** named `captcha-lib`.

---

## Files Created / Modified

| File | Role |
|------|------|
| [__init__.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/__init__.py) | Public API — [Captcha](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/__init__.py#103-297) factory, re-exports |
| [config.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py) | [CaptchaConfig](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#98-180) dataclass, [DifficultyLevel](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#27-39) enum, singleton default config |
| [core/base.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/base.py) | [CaptchaBase](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/base.py#26-117) + [StorageInterface](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/base.py#124-178) ABCs |
| [core/exceptions.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/exceptions.py) | Full exception hierarchy (10 custom exception types) |
| [core/generator.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/generator.py) | [ImageCaptchaGenerator](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/generator.py#25-106) — sync + async rendering pipeline |
| [core/validator.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/validator.py) | [TokenValidator](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/validator.py#35-189) — HMAC signing, expiry, max-attempts, replay protection |
| [utils/randomizer.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/randomizer.py) | All random helpers using `secrets` module |
| [utils/hashing.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/hashing.py) | HMAC sign/verify, SHA-256 answer hashing, token encode/decode |
| [utils/image_utils.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/utils/image_utils.py) | All PIL rendering extracted from original: [draw_character](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#97-143), [create_captcha_image](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/image.py#144-187), noise generators |
| [types/__init__.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py) | Plugin registry: [register_plugin](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py#58-93), [get_plugin](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py#95-112), [list_plugins](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py#114-123), [unregister_plugin](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py#125-138) |
| [types/image.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/image.py) | [ImageCaptcha](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/image.py#34-249) plugin — full refactoring of original, with `.bytes`, `.save()`, async |
| [types/math.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/math.py) | [MathCaptcha](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/math.py#31-216) plugin — arithmetic challenges rendered as images |
| [types/example_plugin.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/example_plugin.py) | [AudioCaptcha](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/example_plugin.py#49-197) stub — fully-documented template for new plugin authors |
| [storage/memory.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/memory.py) | [MemoryStorage](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/memory.py#24-144) — thread-safe LRU dict with TTL expiry |
| [storage/redis.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/redis.py) | [RedisStorage](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/storage/redis.py#27-145) — Redis backend with deferred import |
| [setup.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/setup.py) | pip-installable package with `[redis]` and `[dev]` extras |
| [requirements.txt](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/requirements.txt) | Updated: `Pillow>=10.0.0` (core), optional extras commented |
| [README.md](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/README.md) | Full documentation with API reference, plugin guide, security model |
| [examples/basic_usage.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/examples/basic_usage.py) | Runnable demo of all main features |
| [examples/plugin_demo.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/examples/plugin_demo.py) | [EmojiCaptcha](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/examples/plugin_demo.py#34-102) plugin demo + Observer pattern extension |

---

## Design Patterns Implemented

| Pattern | Where |
|---------|-------|
| **Factory** | `Captcha.create()` — creates any plugin type by name |
| **Strategy** | [DifficultyLevel](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#27-39) presets in [CaptchaConfig](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#98-180) |
| **Plugin / Registry** | `@register_plugin("name")` decorator in [types/__init__.py](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/__init__.py) |
| **Observer** | Subclassing with `super().verify()` hooks (shown in plugin demo) |
| **Dependency Injection** | `storage=` arg to `Captcha.create()` and all plugin [__init__](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/exceptions.py#84-87)s |
| **Singleton** | [get_default_config()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#190-198) / [set_default_config()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/config.py#200-211) thread-safe global |
| **Template Method** | [CaptchaBase](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/base.py#26-117) defines the skeleton; subclasses fill in details |

---

## Security Features

- **HMAC-SHA256 signed tokens** — answer hashes are signed with a secret key; plaintext answers never stored
- **Expiry timestamps** — baked into each token, checked on every [verify()](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/types/image.py#108-143) call
- **Max-attempts enforcement** — raises [CaptchaMaxAttemptsError](file:///d:/VS%20code/Python-Projects/text%20captcha/V3/core/exceptions.py#42-51) after configurable limit
- **Replay attack prevention** — successfully-verified token IDs added to an in-process deny-set
- **Case-insensitive answer hashing** — SHA-256 of the lowercased answer for safe comparison
- **`secrets` module throughout** — all randomness from `secrets.randbelow` / `secrets.choice`

---

## Verification Results

All 10 smoke-test checks passed with `exit code 0`:

```
--- 1. Import chain ---             All imports OK
--- 2. Plugin registry ---          Plugins: ['image', 'math']
--- 3. Config presets ---           Easy: len=4 dots=15 | Hard: len=8 dots=50
--- 4. HMAC hashing ---             sign/verify OK, case-insensitive hash OK
--- 5. Image captcha + storage ---  same storage? True  store has entry: True  wrong -> False
--- 6. Math captcha ---             problem='15 - 4 = ?'
--- 7. Max attempts ---             CaptchaMaxAttemptsError raised correctly
--- 8. Replay protection ---        CaptchaAlreadyUsedError raised correctly
--- 9. to_dict ---                  keys: ['captcha_type','captcha_id','token',...]
--- 10. Random utils ---            chars OK, color OK, math OK
=================================================
   ALL 10 CHECKS PASSED
=================================================
```

---

## Quick Install

```bash
cd "d:\VS code\Python-Projects\text captcha\V3"
pip install -e .
```

Then in any Python file:

```python
from captcha_lib import Captcha
captcha = Captcha.create()
captcha.save("challenge.png")
ok = captcha.verify(user_input)
```
