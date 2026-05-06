# InnoCaptcha — Security & Code Review Report
**Branch:** `devmode` | **Version:** 2.3.0  
**Reviewed by:** Senior Security & Code Analyst  
**Date:** 2026-05-05

---

## 🔴 Critical — Security Vulnerabilities

### 1. Encryption Key Stored Inside the Same Database It Protects
**File:** `utils.py` — `_initialize_schema()`

```python
self.cursor.execute("""CREATE TABLE IF NOT EXISTS encryption_key (value TEXT)""")
```

**المشكلة:**  
مفتاح التشفير بيتحفظ جوه نفس قاعدة البيانات اللي بيحمي البيانات فيها. ده بيخلي التشفير بتاعك **زيرو value** من ناحية أمنية — أي حد يوصل للـ DB بياخد المفتاح والـ answers في نفس الوقت.

**الحل:**  
- استخدم environment variable: `os.environ.get("INNOCAPTCHA_KEY")`
- أو اكتبه في ملف منفصل خارج الـ package directory
- أو استخدم مكتبة زي `python-keyring` أو `aws-secretsmanager`

---

### 2. SQL Injection عبر Table Names
**File:** `utils.py` — `_initialize_schema()`

```python
tables = ['text', 'audio', 'math', 'voice', 'image']
for table in tables:
    self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ...")
    self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN ip_address TEXT")
```

**المشكلة:**  
الـ table names بتتدخل مباشرة في الـ SQL query عن طريق f-string من غير أي sanitization. لو الـ `tables` list اتعدلت بأي طريقة (أو لو حصل تطوير مستقبلي وخلى الـ table name يجي من input خارجي)، هيبقى في SQL injection.

**الحل:** استخدم allowlist صارمة وتحقق منها قبل interpolation:
```python
ALLOWED_TABLES = {'text', 'audio', 'math', 'voice', 'image'}
assert table in ALLOWED_TABLES
```

---

### 3. Race Condition في الـ Attempt Counter
**Files:** `text.py`, `audio.py`, `math.py`, `image.py`, `voice.py`

```python
# Check
if attempts >= 5: return "Max attempts reached"
# ... ثم لاحقاً
# Update
db.execute("UPDATE text SET attempts = attempts + 1 WHERE id = ?", (self.id,))
```

**المشكلة:**  
الـ check والـ update مش atomic. في بيئة concurrent (زي أي web server)، ممكن يتبعت 10 requests في نفس الوقت، كلهم يشوفوا `attempts = 4`، وكلهم يعدوا. ده بيكسر الـ rate limiting كلياً.

**الحل:** استخدم atomic UPDATE مع conditional:
```python
db.execute("""
    UPDATE text SET attempts = attempts + 1 
    WHERE id = ? AND attempts < 5
""", (self.id,))
# ثم check rowcount
```

---

### 4. Timing Attack في مقارنة الـ Context Binding
**Files:** جميع الـ `verify()` methods

```python
if (db_ip and ip and db_ip != ip) or (db_session and session_id and db_session != session_id):
```

**المشكلة:**  
المقارنة دي بتستخدم `!=` العادية بدل `secrets.compare_digest()`. ده بيفتح الباب لـ timing attacks على الـ IP والـ session_id.

**الحل:**
```python
ip_match = not (db_ip and ip) or secrets.compare_digest(db_ip, ip)
session_match = not (db_session and session_id) or secrets.compare_digest(db_session, session_id)
if not ip_match or not session_match: ...
```

---

### 5. الـ Encryption Key بيتقرأ بالـ `limit 1` من غير ترتيب
**Files:** كل الـ modules

```python
db.execute("SELECT value FROM encryption_key limit 1")
```

**المشكلة:**  
`LIMIT 1` من غير `ORDER BY` بترجع أي row عشوائي من الـ DB. لو في أكتر من row في الجدول ده (بسبب bug أو migration قديم)، ممكن يتقرأ مفتاح غلط ويفشل الـ decryption.

**الحل:**
```python
db.execute("SELECT value FROM encryption_key ORDER BY rowid DESC LIMIT 1")
```

---

### 6. الـ Database Connection مش بتتعمل Close في حالة الـ Exception
**File:** `utils.py` — `DB` class

```python
def __init__(self, db_path=None):
    self.conn = sqlite3.connect(self.db_path)  # لو حصل error بعد كده
    ...
```

**المشكلة:**  
لو `_initialize_schema()` رمت exception، الـ connection مش هيتعمل close لأن `__exit__` مش هيتكال. ده connection leak.

**الحل:** استخدم try/finally جوه `__init__` أو اعتمد بشكل كامل على الـ context manager.

---

## 🟠 High — مشاكل تصميم وأداء

### 7. Cleanup Thread بيشتغل مع كل instantiation
**Files:** `text.py`, `audio.py`, `image.py`, `voice.py`

```python
threading.Thread(target=self.cleanup, daemon=True).start()
```

**المشكلة:**  
كل ما تعمل `TextCaptcha()` جديد بيتعمل thread جديد بيفتح DB connection وبيعمل DELETE. لو عندك 1000 request/second، هيبقى عندك 1000 thread بيشتغلوا في نفس الوقت بيعملوا نفس الشغل.

**الحل:** استخدم scheduler منفصل (APScheduler مثلاً) أو cleanup بيشتغل مرة كل X دقيقة على مستوى الـ module.

---

### 8. الـ `__init__.py` بيعمل `from . import *`
**File:** `__init__.py`

```python
from . import *
```

**المشكلة:**  
ده wildcard import — بيستورد كل حاجة من كل الـ submodules من غير تحكم. بيبطئ الـ import، وبيلوث الـ namespace، وممكن يسبب circular imports مستقبلاً.

**الحل:**
```python
from .text import TextCaptcha
from .audio import AudioCaptcha
from .math import MathCaptcha
from .voice import VoiceCaptcha
from .image import ImageCaptcha
```

---

### 9. الـ DB Object مش بيعمل `close()` في الـ `execute()` helper
**File:** `utils.py`

الـ `DB` class عندها `__exit__` بيعمل `close()`، لكن الـ `execute()` و`commit()` و`fetchone()` methods بتسمح باستخدام الـ object من غير context manager — ولو حصل exception، الـ connection مش هيتقفل.

---

### 10. الـ `MathCaptcha.cleanup()` هي `@staticmethod` بس الباقي instance methods
**File:** `math.py`

```python
@staticmethod
def cleanup():
    with DB() as db: ...
```

بينما في `text.py`:
```python
def cleanup(self):
    with DB(db_path=DB_PATH) as db: ...
```

**المشكلة:** تناقض في الـ design بين الـ modules. `MathCaptcha` مش بيبدأ cleanup thread في `__init__()` خالص — يعني الـ expired math captchas مش بتتمسح تلقائياً.

---

### 11. الـ `ImageCaptcha` بيلود YOLO Model في كل instantiation
**File:** `image.py`

```python
def __init__(self, lang='en'):
    self.model = YOLO(MODEL_PATH)
```

**المشكلة:**  
تحميل YOLO model بياخد وقت وذاكرة كبيرة. لو اتعمل 100 `ImageCaptcha()` في الوقت الواحد، هيتحمل الـ model 100 مرة.

**الحل:** استخدم module-level singleton:
```python
_yolo_model = None
def _get_model():
    global _yolo_model
    if _yolo_model is None:
        _yolo_model = YOLO(MODEL_PATH)
    return _yolo_model
```

---

## 🟡 Medium — مشاكل الكود والـ Logic

### 12. الـ Tests بايظة بسبب التشفير
**File:** `test_innocaptcha.py`

```python
def test_create_inserts_row_in_db(self):
    ...
    self.assertEqual(row[1], self.captcha.chars)  # هيفشل!
```

**المشكلة:**  
الـ test بيقرأ الـ `answer` من الـ DB ويقارنه بـ `self.captcha.chars` مباشرة، لكن الـ answer دلوقتي مشفر بـ Fernet. كمان الـ `test_create_sets_chars_max_6` و`test_create_uses_provided_chars` بيوصل لـ `self.captcha.chars` بعد `create()` اللي بيعمل `del self.chars` — هيرجع `AttributeError`.

---

### 13. `del self.chars` بيكسر الـ API الـ public
**Files:** `text.py`, `audio.py`

```python
del self.chars  # Remove plaintext answer from memory
```

**المشكلة:**  
الـ `del` ده بيكسر أي حاجة تحاول تعمل `captcha.chars` بعد `create()`. الـ tests الحالية بتعمل كده وبتفشل. وأي مستخدم للـ library ممكن يعمل نفس الغلطة.

**الحل:** خلي `self.chars = None` بدل `del`، أو وثّق بوضوح إن الـ property دي بتبقى `None` بعد `create()`.

---

### 14. الـ `VoiceCaptcha` بتعمل `del` على الـ phrase بطريقة خاطئة
**File:** `voice.py`

```python
# في create():
self.phrase = fernet.encrypt(self.phrase.encode())  # بقت bytes مش string!
db.execute("INSERT INTO voice ... VALUES (?, ...)", (self.id, self.phrase, ...))
# ما فيش del للـ phrase بعد كده
```

**المشكلة:**  
بعد التشفير، `self.phrase` بقت `bytes` (الـ ciphertext) مش الـ plaintext. وما فيش `del self.phrase` زي باقي الـ modules. الـ phrase المشفرة فاضلة في الـ object.

---

### 15. الـ `AudioCaptcha` بتقبل `chars` كـ string بس بتتعاملها كـ list
**File:** `audio.py`

```python
def create(self, chars=None, ...):
    if chars:
        if not all(isinstance(c, str) and len(c) == 1 for c in chars): ...
    self.chars = "".join(chars[:6])
```

**المشكلة:**  
لو بعتت `chars="ABCDEF"` (string)، الـ validation بتعدي (كل character هي string طول 1)، بس `"".join(chars[:6])` بيشتغل صح. التناقض ده مش موثق.

---

### 16. الـ `UploadToGitHub.py` موجود في الـ package
**File:** `UploadToGitHub.py`

```python
ServerURL = "https://innocaptcha.midoghanam.site"
```

**المشكلة:**  
ملف scripts خاص بالـ development/deployment موجود في الـ root والمفروض يكون في `.gitignore` أو `scripts/` folder منفصلة. كمان `setup.py` فيه نفس الـ `ServerURL`.

---

### 17. الـ `TextCaptcha.color` Generation قد ينتج نفس اللون للـ text والـ background
**File:** `text.py`

```python
base = secrets.randbelow(101) + 80
shift = (secrets.randbelow(56) + 45) * (1 - 2 * secrets.randbelow(2))
self.background = (base, ...)
self.text_color = tuple(max(0, min(255, c + shift)) for c in self.background)
```

**المشكلة:**  
الـ `shift` ممكن يبقى 45 أو 100 positive أو negative. لو `base = 155` و`shift = -45`، النتيجة `110` — الفرق مش كافي. ممكن ينتج captcha شبه مش مقروء.

**الحل:** تحقق إن الـ contrast ratio كافٍ (WCAG minimum 4.5:1 للـ text).

---

## 🔵 Low — تحسينات وـ Best Practices

### 18. لا يوجد Type Hints
كل الـ methods من غير type annotations. ده بيقلل الـ IDE support وبيصعّب الـ code review.

```python
# الحالي
def create(self, chars=None, ip=None, session_id=None):

# المقترح
def create(self, chars: list[str] | None = None, ip: str | None = None, session_id: str | None = None) -> str:
```

---

### 19. الـ `verify()` بترجع 3 أنواع مختلفة
في كل الـ modules، `verify()` بترجع:
- `True` (bool) لو صح
- `False` (bool) لو غلط  
- `str` (error message) في حالات الـ error

ده بيصعّب على المستخدم الـ error handling. الأفضل:
- إرجاع `True/False` بس
- رمي Exceptions مسماة: `CaptchaExpiredError`, `MaxAttemptsError`, `CaptchaNotFoundError`

---

### 20. الـ `setup.py` والـ `pyproject.toml` موجودين مع بعض
الاتنين بيعرفوا نفس الـ metadata وبيخلقوا تناقض محتمل. المعيار الحديث (PEP 517+) هو استخدام `pyproject.toml` فقط.

---

### 21. الـ `requests` كـ build dependency في `pyproject.toml`
```toml
[build-system]
requires = ["setuptools>=42", "wheel", "requests"]
```

**المشكلة:** `requests` مش build tool — مش محتاجة في وقت البناء. دي runtime dependency.

---

### 22. الـ `setup_logging()` بيتكال في كل مرة `log_event()` بيشتغل
**File:** `utils.py`

```python
def log_event(event_type, message, metadata=None):
    setup_logging()  # بيتكال في كل log
    ...
```

`logging.basicConfig()` مش بيعيد التهيئة لو اللوجر موجود أصلاً، لكن الفعل ده نفسه تكلفة زيادة. الأفضل استخدام `logging.getLogger()` بشكل صحيح.

---

### 23. الـ `MathCaptcha` مش بيلود font مرة واحدة
**File:** `math.py`

`_load_font()` بتعمل `os.listdir(font_dir)` في كل مرة بتترسم token. لو في 7 tokens، بيعمل 7 disk reads. الأفضل load الـ font list مرة واحدة في `__init__`.

---

### 24. الـ `AudioCaptcha` بتستخدم `np.random` مش `secrets`
**File:** `audio.py`

```python
noise = np.random.uniform(-noise_scale, noise_scale, len(samples))
```

`np.random` مش cryptographically secure. للـ noise في captcha ده مقبول، لكن يستحق يتوثق أو يتغير.

---

### 25. الـ `ImageCaptcha` عندها `correct_grids` ممكن تبقى فاضية
**File:** `image.py`

لو YOLO ملقاش أي objects في الصورة، `correct_grids` بتبقى empty set، والـ answer بيبقى empty string `""`. المستخدم مش هيعرف أي grid يختار — ده UX problem وممكن يبقى security issue.

---

## 📋 ملخص حسب الأولوية

| # | المشكلة | الخطورة | الـ File |
|---|---------|---------|---------|
| 1 | Encryption key in same DB | 🔴 Critical | `utils.py` |
| 2 | SQL injection via table names | 🔴 Critical | `utils.py` |
| 3 | Race condition in attempt counter | 🔴 Critical | All modules |
| 4 | Timing attack on context binding | 🔴 Critical | All modules |
| 5 | `LIMIT 1` without `ORDER BY` on key | 🔴 Critical | All modules |
| 6 | DB connection leak on exception | 🟠 High | `utils.py` |
| 7 | Cleanup thread on every init | 🟠 High | All modules |
| 8 | Wildcard `from . import *` | 🟠 High | `__init__.py` |
| 9 | DB not closed on exception (no CM) | 🟠 High | `utils.py` |
| 10 | `MathCaptcha.cleanup()` inconsistency | 🟠 High | `math.py` |
| 11 | YOLO reloaded on every init | 🟠 High | `image.py` |
| 12 | Tests broken by encryption | 🟡 Medium | `test_innocaptcha.py` |
| 13 | `del self.chars` breaks public API | 🟡 Medium | `text.py`, `audio.py` |
| 14 | `VoiceCaptcha` phrase not cleared | 🟡 Medium | `voice.py` |
| 15 | `AudioCaptcha` string/list ambiguity | 🟡 Medium | `audio.py` |
| 16 | `UploadToGitHub.py` in package root | 🟡 Medium | Root |
| 17 | Low contrast text/background | 🟡 Medium | `text.py` |
| 18 | No type hints | 🔵 Low | All modules |
| 19 | `verify()` returns 3 types | 🔵 Low | All modules |
| 20 | Dual `setup.py` + `pyproject.toml` | 🔵 Low | Root |
| 21 | `requests` as build dependency | 🔵 Low | `pyproject.toml` |
| 22 | `setup_logging()` called every log | 🔵 Low | `utils.py` |
| 23 | Font list re-read on every token | 🔵 Low | `math.py` |
| 24 | `np.random` instead of `secrets` | 🔵 Low | `audio.py` |
| 25 | Empty `correct_grids` edge case | 🔵 Low | `image.py` |

---

## 🚀 اقتراحات تطوير مستقبلية

1. **Redis Backend** — استبدال SQLite بـ Redis لأي deployment إنتاجي (أسرع، atomic operations، TTL built-in)
2. **Async Support** — إضافة `async def create()` و`async def verify()` لدعم FastAPI/async frameworks
3. **CAPTCHA Difficulty Levels** — إضافة `difficulty='easy'|'medium'|'hard'` للـ constructors
4. **Webhook/Callback** — إرسال event عند كل verify لأغراض التحليل
5. **Framework Integrations** — مكتبات منفصلة: `innocaptcha-django`, `innocaptcha-flask`, `innocaptcha-fastapi`
6. **Proper Exceptions Module** — ملف `exceptions.py` بيعرف: `CaptchaExpiredError`, `MaxAttemptsError`, `CaptchaNotFoundError`, `DecryptionError`
7. **CI/CD Tests** — إضافة GitHub Actions workflow للـ automated testing
8. **Coverage Report** — الـ test file الحالي بيغطي TextCaptcha بشكل جيد لكن ImageCaptcha وVoiceCaptcha غير مغطيين تقريباً

---

*هذا التقرير يغطي الـ `devmode` branch كاملاً. الأولوية القصوى هي حل المشاكل الـ 5 الأولى (Critical) قبل أي release.*
