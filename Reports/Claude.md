# 🔐 InnoCaptcha — Security Audit & Improvement Report
**Branch:** `devmode` | **Version:** `2.4.0`  
**Audited by:** Senior Security Analyst (40yr XP)  
**Date:** 2026-05-10  

---

## 📊 Executive Summary

| Severity | Count |
|---|---|
| 🔴 Critical | 5 |
| 🟠 High | 5 |
| 🟡 Medium | 8 |
| 🟢 Low / Improvement | 10 |
| **Total** | **28** |

---

## 🔴 CRITICAL — يجب إصلاحها فوراً

---

### [C-1] `package_data` ينشر الـ Secret Key مع الـ Package

**الملف:** `setup.py` و `pyproject.toml`

```python
# setup.py
package_data={"InnoCaptcha": ["**/*"]}

# pyproject.toml
[tool.setuptools.package-data]
InnoCaptcha = ["**/*"]
```

**المشكلة:**  
لو `data/secret.key` موجود وقت البيلد، هيتضمن جوا الـ `.whl` أو `.tar.gz` المنشور على PyPI. ده معناه كل المستخدمين هيبقى عندهم نفس مفتاح التشفير — بيدمر كامل نموذج الأمان.

**الإصلاح:**
```python
# pyproject.toml — exclude ملفات حساسة
[tool.setuptools.package-data]
InnoCaptcha = ["data/fonts/**", "data/audios/**", "data/images/**", "data/models/**"]
# لا تضمن *.key ولا dbs ولا logs
```

---

### [C-2] Return Type غير متسق في `verify()` — خطر تجاوز الأمان

**الملف:** جميع الموديولات (`text.py`, `math.py`, `audio.py`, `voice.py`, `image.py`)

```python
# verify() بترجع ثلاث أنواع مختلفة:
return True         # صح
return False        # غلط
return "Captcha expired"   # string (truthy!) ← الخطر
return "Max attempts reached"  # string (truthy!)
```

**المشكلة:**  
أي مطور يكتب الكود ده:
```python
if captcha.verify(user_input):  # ✅ يبان صح
    grant_access()
```
... هيبقى بيدي access وقت انتهاء الصلاحية، وقت تجاوز المحاولات، وعند خطأ في السياق — لأن الـ strings كلها truthy في Python.

**الإصلاح:**  
استخدم Custom Exception أو Enum بدل الـ strings:
```python
class CaptchaResult:
    SUCCESS = True
    FAILED  = False

class CaptchaExpiredError(Exception): pass
class CaptchaMaxAttemptsError(Exception): pass
class CaptchaContextError(Exception): pass
class CaptchaNotFoundError(Exception): pass
```

أو على أقل تقدير رجّع دايمًا `bool`:
```python
# بدل:
return "Captcha expired"
# استخدم:
raise CaptchaExpiredError("CAPTCHA has expired")
```

---

### [C-3] Race Condition في YOLO Singleton — غير Thread-Safe

**الملف:** `image.py`

```python
_yolo_model = None

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:           # ← Thread A وصل هنا
        MODEL_PATH = ...
        _yolo_model = YOLO(MODEL_PATH) # ← Thread B وصل هنا كمان
    return _yolo_model
```

**المشكلة:**  
في بيئات multi-threaded (Gunicorn, uWSGI, FastAPI async)، تريدين مختلفين ممكن يشوفوا `_yolo_model is None` في نفس الوقت وكلاهما يحاول يحمّل الموديل. ده ممكن يسبب corruption أو double-loading يأكل RAM.

**الإصلاح:**
```python
import threading

_yolo_model = None
_yolo_lock  = threading.Lock()

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        with _yolo_lock:
            if _yolo_model is None:   # Double-checked locking
                _yolo_model = YOLO(MODEL_PATH)
    return _yolo_model
```

---

### [C-4] CAPTCHA قابل للتخطي لو YOLO ما لقاش Objects

**الملف:** `image.py`

```python
correct_grids = set()
for (x1, y1, x2, y2) in self.annotation_coordinates:
    for grid_num, (gx1, gy1, gx2, gy2) in grid_mapping.items():
        if not (x2 < gx1 or x1 > gx2 or y2 < gy1 or y1 > gy2):
            correct_grids.add(grid_num)

answer = ",".join(map(str, sorted(correct_grids)))  # ← "" لو مفيش objects
```

**المشكلة:**  
لو YOLO ما اكتشفش الـ object في الصورة، `correct_grids` فارغة، و `answer = ""`. مهاجم يعرف ده يقدر يـsubmit string فارغة ويعدي الـ CAPTCHA.

**الإصلاح:**
```python
if not correct_grids:
    raise RuntimeError("YOLO detected no target objects in image. Choose a different image.")
```
أو أعد اختيار صورة أوتوماتيك لحد ما يلاقي objects.

---

### [C-5] SQL Injection Pattern في `_initialize_schema()`

**الملف:** `utils.py`

```python
for table in ALLOWED_TABLES:
    self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {table} ...""")  # ← f-string!
    self.cursor.execute(f"PRAGMA table_info({table})")
    self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN ip_address TEXT")
```

**المشكلة:**  
حاليًا `ALLOWED_TABLES` hardcoded وآمنة. لكن استخدام f-strings مع SQL هو anti-pattern خطير — لو حد عدّل `ALLOWED_TABLES` أو وصل لها بأي شكل، injection فوري. SQLite مش بتدعم parameterized identifiers، لكن الحل الصح هو whitelisting صريح.

**الإصلاح:**
```python
ALLOWED_TABLES = frozenset({'text', 'audio', 'math', 'voice', 'image'})

def _safe_table(self, name: str) -> str:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Invalid table name: {name!r}")
    return name  # استخدمها بعد التحقق

# ثم:
table = self._safe_table(table)
self.cursor.execute(f"CREATE TABLE IF NOT EXISTS {table} ...")  # آمن بعد الwhitelisting
```
الأهم — اعمل unit test صريح يتأكد إن أي اسم جديد بيرفع ValueError.

---

## 🟠 HIGH — إصلاح أولوية عالية

---

### [H-1] Secret Key مخزن جوا Package Directory

**الملف:** `utils.py`

```python
SECRET_KEY_PATH = os.path.join(BASE_DIR, 'data/secret.key')
```

**المشكلة:**  
- لو المستخدم عمل `pip install --upgrade InnoCaptcha`، الـ `data/` directory ممكن يتحذف/يتعاد — ومعاه الـ key، وبكده كل الـ CAPTCHAs المخزنة بتبقى غير قابلة للفك.
- في shared hosting، users تانيين ممكن يقرأوا الملف.

**الإصلاح:**
```python
import platformdirs  # pip install platformdirs

def get_secret_key_path():
    data_dir = platformdirs.user_data_dir("InnoCaptcha", "InnoSoft")
    os.makedirs(data_dir, mode=0o700, exist_ok=True)
    return os.path.join(data_dir, "secret.key")
```
أو على أقل تقدير، وضّح في الـ docs إن المستخدم لازم يبقى عنده `INNOCAPTCHA_KEY` في الـ environment.

---

### [H-2] `np.random` في Audio بدل Secure Random

**الملف:** `audio.py`

```python
noise = np.random.uniform(-noise_scale, noise_scale, len(samples)).astype(np.float32)
```

**المشكلة:**  
`np.random` بيستخدم Mersenne Twister — predictable PRNG. مهاجم يعرف الـ seed يقدر يتنبأ بالـ noise ويعمل audio fingerprinting.

**الإصلاح:**
```python
rng = np.random.default_rng(int.from_bytes(os.urandom(8), 'big'))
noise = rng.uniform(-noise_scale, noise_scale, len(samples)).astype(np.float32)
```

---

### [H-3] VoiceCaptcha بتبعت Audio لـ Google بدون Privacy Notice

**الملف:** `voice.py`

```python
transcript = self.recognizer.recognize_google(audio_data, language=self.language)
```

**المشكلة:**  
صوت المستخدم بيتبعت لـ Google Speech-to-Text API (خارجي، مجاني، بيلوج البيانات). ده:
- مخالف للـ GDPR لو بتستخدمه في EU بدون consent
- مش موثق في الـ README
- هيفشل بدون internet وبدون توضيح

**الإصلاح:**
1. أضف في الـ docs: `⚠️ VoiceCaptcha sends audio data to Google's STT API`
2. خلي المستخدم يقدر يوفر STT alternative:
```python
class VoiceCaptcha:
    def __init__(self, language='en-US', stt_engine='google'):
        self.stt_engine = stt_engine  # 'google' | 'whisper' | 'custom'
```
3. أضف دعم لـ local models زي `openai-whisper`.

---

### [H-4] `phrase` مش بيتمسح من الذاكرة بعد `create()`

**الملف:** `voice.py`

```python
def create(self, phrase=None, ...):
    self.phrase = secrets.choice(phrases)  # ← بيفضل في الذاكرة
    # لا يوجد: self.phrase = None
```

**المشكلة:**  
`text.py` و `audio.py` بيعملوا `self.chars = None` بعد التشفير وإدراج الـ DB، لكن `voice.py` مش بيمسح الـ `phrase`. ده inconsistency أمنية.

لكن كمان: الـ CLI بيطبع الـ phrase:
```python
print(f"🗣️  Please read this phrase out loud: '{cap.phrase}'")
```
ده مقصود — لكن المفروض يتمسح بعد الطباعة.

**الإصلاح:**
```python
# في نهاية create():
returned_phrase = self.phrase
self.phrase = None
return self.id  # المستخدم يجيب الـ phrase من DB لو محتاجها
```

---

### [H-5] Version مكررة في 3 أماكن منفصلة

**الملف:** `__init__.py`، `setup.py`، `pyproject.toml`

```python
# __init__.py
__version__ = "2.4.0"

# setup.py
__version__ = "2.4.0"

# pyproject.toml
version = "2.4.0"
```

**المشكلة:**  
نسيت تعدّل واحدة = release بإصدار خاطئ. حصل ده فعلاً في مشاريع كتير.

**الإصلاح:**
```toml
# pyproject.toml — single source of truth
[project]
version = "2.4.0"
```

```python
# __init__.py
from importlib.metadata import version
__version__ = version("InnoCaptcha")
```

```python
# setup.py — احذفه خالص، pyproject.toml كافي
```

---

## 🟡 MEDIUM — إصلاح في أقرب وقت

---

### [M-1] `setup_logging()` بيتنادى مع كل `log_event()`

**الملف:** `utils.py`

```python
def log_event(event_type, message, metadata=None):
    setup_logging()  # ← بيتنادى في كل event!
    logging.info(...)
```

`logging.basicConfig()` بيعمل no-op بعد أول نداء، لكن الـ function call نفسها overhead على كل log event.

**الإصلاح:**
```python
_logging_initialized = False

def log_event(event_type, message, metadata=None):
    global _logging_initialized
    if not _logging_initialized:
        setup_logging()
        _logging_initialized = True
    logging.info(...)
```

---

### [M-2] لا يوجد Connection Pooling للـ SQLite

**الملف:** `utils.py`

كل `verify()` أو `create()` بيفتح connection جديد ويقفله. في load عالي (مثلاً 1000 req/s)، ده overhead ضخم.

**الإصلاح:**
استخدم `threading.local()` لـ per-thread connections:
```python
import threading
_local = threading.local()

def get_connection():
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return _local.conn
```
أو استخدم `sqlalchemy` مع connection pool.

---

### [M-3] Color Contrast مش مضمون في TextCaptcha

**الملف:** `text.py`

```python
base  = secrets.randbelow(101) + 80  # 80-180
shift = (secrets.randbelow(56) + 45) * (1 - 2 * secrets.randbelow(2))  # ±(45-100)
self.background = (base, secrets.randbelow(101)+80, secrets.randbelow(101)+80)
self.text_color = tuple(max(0, min(255, c + shift)) for c in self.background)
```

`shift` ممكن يكون صغير جداً وإذا channels متقاربة، النص يبقى غير قابل للقراءة — وبالتالي الـ bot هيحلها أسهل من الإنسان.

**الإصلاح:**
```python
def _ensure_contrast(bg, fg, min_diff=80):
    """Ensure luminance difference >= min_diff"""
    bg_lum = 0.299*bg[0] + 0.587*bg[1] + 0.114*bg[2]
    fg_lum = 0.299*fg[0] + 0.587*fg[1] + 0.114*fg[2]
    return abs(bg_lum - fg_lum) >= min_diff
```

---

### [M-4] لا يوجد Sample Rate Validation في `read_wav()`

**الملف:** `audio.py`

```python
def read_wav(path):
    with wave.open(path, 'rb') as wf:
        channels  = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())
        # ← مفيش تحقق من sample rate!
```

لو ملف `.wav` عنده `framerate = 22050` بدل `44100`، الصوت هيتشغل بسرعة ضعف وهيبقى غير مفهوم.

**الإصلاح:**
```python
EXPECTED_RATE = 44100

def read_wav(path):
    with wave.open(path, 'rb') as wf:
        if wf.getframerate() != EXPECTED_RATE:
            raise ValueError(f"{path}: expected {EXPECTED_RATE}Hz, got {wf.getframerate()}Hz")
        ...
```

---

### [M-5] `threading` Import غير مستخدم في `text.py`

**الملف:** `text.py`

```python
import os, secrets, threading  # ← threading مش مستخدمة
```

**الإصلاح:**
```python
import os, secrets
```
افحص باستخدام `flake8` أو `ruff` — هيكتشف كل الـ unused imports.

---

### [M-6] `image.py` — `save()` بتحفظ في CWD بصمت

**الملف:** `image.py`

```python
def save(self, path=None):
    ...
    if not path:
        path = "captcha_image.png"  # ← صامت وغير متوقع
    final_image.save(path)
```

**الإصلاح:**
```python
def save(self, path):
    if path is None:
        raise ValueError("path is required. Example: cap.save('output.png')")
    ...
```

---

### [M-7] `math.py` — `verify()` و `cleanup()` بيستخدموا `DB()` بدون `db_path`

**الملف:** `math.py`

```python
def create(self, ...):
    with DB(db_path=DB_PATH) as db:  # ← صريح

def verify(self, ...):
    with DB() as db:  # ← ضمني (يعتمد على default)

def cleanup():
    with DB() as db:  # ← ضمني
```

**الإصلاح:** استخدم `DB(db_path=DB_PATH)` في كل مكان بشكل متسق.

---

### [M-8] `UploadToGitHub.py` في الـ Repository

**الملف:** `UploadToGitHub.py`

script مساعد للرفع على GitHub موجود في الـ public repo. ده ممكن يحتوي على tokens أو workflow خاص مش المفروض يتشاف.

**الإصلاح:** انقله لـ `.github/scripts/` أو احذفه من الـ repo وخليه locally.

---

## 🟢 LOW / IMPROVEMENTS — تحسينات مقترحة

---

### [L-1] لا يوجد Type Hints

الكود بالكامل بدون type annotations. ده بيصعّب الـ IDE support والمراجعة.

```python
# بدل:
def create(self, chars=None, ip=None, session_id=None):

# استخدم:
def create(
    self,
    chars: list[str] | str | None = None,
    ip: str | None = None,
    session_id: str | None = None,
) -> str:
```

---

### [L-2] `__init__.py` بدون `__all__`

```python
# حاليًا:
from .text  import TextCaptcha
from .audio import AudioCaptcha
...

# أضف:
__all__ = ["TextCaptcha", "AudioCaptcha", "MathCaptcha", "VoiceCaptcha", "ImageCaptcha"]
```

---

### [L-3] `DB` Class مش فيها `fetchall()`

```python
class DB:
    def fetchone(self): return self.cursor.fetchone()
    # مفيش fetchall!
```

أضف:
```python
def fetchall(self): return self.cursor.fetchall()
```

---

### [L-4] Tests بتستخدم `eval()` على String خارجي

**الملف:** `test_innocaptcha.py`

```python
q = self.captcha.question.replace('×', '*')
self.raw_answer = str(eval(q))  # ← eval!
```

حتى لو `question` داخلي، ده bad practice في الـ tests.

**الإصلاح:**
```python
import operator

OPS = {'+': operator.add, '-': operator.sub, '×': operator.mul, '*': operator.mul}
# Parse manually بدل eval
```

---

### [L-5] Tests لا تغطي `ImageCaptcha` و `VoiceCaptcha`

Test coverage لـ `ImageCaptcha` = 0%، `VoiceCaptcha` = 0%.

أضف:
```python
class TestImageCaptcha(unittest.TestCase):
    def test_create_fails_without_yolo_model(self): ...
    def test_empty_grids_raises_error(self): ...

class TestVoiceCaptcha(unittest.TestCase):
    def test_create_sets_id(self): ...
    def test_phrase_cleared_after_create(self): ...
```

---

### [L-6] Tests لا تختبر Context Binding (ip/session)

```python
# مفيش test زي ده:
def test_verify_fails_on_ip_mismatch(self):
    self.captcha.create(chars='ABC', ip='1.2.3.4')
    result = self.captcha.verify('ABC', ip='9.9.9.9')
    self.assertNotEqual(result, True)
```

---

### [L-7] `CLI verify` لا تدعم `--lang` لـ Arabic CAPTCHAs

**الملف:** `cli.py`

`--lang` أضيف لـ `gen_parser` بس، مش لـ `ver_parser`. الكود بيحاول `hasattr(args, 'lang')` لكنه دايمًا False للـ verify — بيعني ما تقدرش تتحقق من Arabic CAPTCHA عبر الـ CLI بلغة صح.

**الإصلاح:**
```python
ver_parser.add_argument("--lang", choices=["en", "ar", "en-US", "ar-EG"], default="en")
```

---

### [L-8] `setup.py` متاح جنب `pyproject.toml` (redundant)

Modern Python packaging (PEP 517/518) بيستخدم `pyproject.toml` فقط. وجود الاتنين مع بعض بيسبب confusion وممكن يعمل conflicts.

**الإصلاح:** احذف `setup.py` وخلّي `pyproject.toml` فقط.

---

### [L-9] لا يوجد `INNOCAPTCHA_DB_PATH` Environment Variable

المستخدمين مش قادرين يغيروا مكان الـ database إلا لو عدّلوا الكود. أضف:

```python
DB_PATH = os.environ.get(
    'INNOCAPTCHA_DB_PATH',
    os.path.join(BASE_DIR, 'data/dbs/captcha.db')
)
```

---

### [L-10] YOLO Confidence Threshold مش قابل للتعديل

```python
results = self.model(img)  # ← default confidence = 0.25
```

Low-confidence detections (>25%) ممكن تخلي الـ answer غلط. أضف parameter:

```python
class ImageCaptcha:
    def __init__(self, lang='en', yolo_confidence=0.5):
        self.yolo_confidence = yolo_confidence
    
    def create(self, ...):
        results = self.model(img, conf=self.yolo_confidence)
```

---

## 📋 Remediation Priority Matrix

| ID | Issue | File | Priority | Effort |
|---|---|---|---|---|
| C-1 | package_data ينشر secret.key | setup.py / pyproject.toml | 🔴 فوري | منخفض |
| C-2 | verify() return type inconsistency | جميع الموديولات | 🔴 فوري | عالي |
| C-3 | YOLO race condition | image.py | 🔴 فوري | منخفض |
| C-4 | Empty grids bypass | image.py | 🔴 فوري | منخفض |
| C-5 | SQL f-string pattern | utils.py | 🔴 فوري | منخفض |
| H-1 | Secret key في package dir | utils.py | 🟠 عالي | متوسط |
| H-2 | np.random في audio | audio.py | 🟠 عالي | منخفض |
| H-3 | Google STT privacy | voice.py | 🟠 عالي | متوسط |
| H-4 | phrase مش بيتمسح | voice.py | 🟠 عالي | منخفض |
| H-5 | Version في 3 أماكن | setup.py, init, toml | 🟠 عالي | منخفض |
| M-1 | setup_logging كل event | utils.py | 🟡 متوسط | منخفض |
| M-2 | No connection pooling | utils.py | 🟡 متوسط | عالي |
| M-3 | Color contrast | text.py | 🟡 متوسط | منخفض |
| M-4 | Sample rate validation | audio.py | 🟡 متوسط | منخفض |
| M-5 | Unused threading import | text.py | 🟡 متوسط | منخفض |
| M-6 | save() silent CWD | image.py | 🟡 متوسط | منخفض |
| M-7 | Inconsistent DB() calls | math.py | 🟡 متوسط | منخفض |
| M-8 | UploadToGitHub.py في repo | root | 🟡 متوسط | منخفض |

---

## 🛠️ Recommended Tooling

أضف لـ CI/CD:

```bash
# Static Analysis
pip install ruff mypy bandit

ruff check InnoCaptcha/          # lint + unused imports
mypy  InnoCaptcha/               # type checking
bandit -r InnoCaptcha/           # security scan

# Tests with coverage
pytest test_innocaptcha.py --cov=InnoCaptcha --cov-report=html
```

أضف `.github/workflows/security.yml`:
```yaml
name: Security Scan
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit ruff
      - run: bandit -r InnoCaptcha/ -ll
      - run: ruff check InnoCaptcha/
```

---

## ✅ ما تم صح (Positive Findings)

- ✅ استخدام `secrets` بدل `random` في معظم الأماكن
- ✅ `secrets.compare_digest()` لمقارنة الإجابات (timing-safe)
- ✅ تشفير الإجابات في الـ DB بـ Fernet
- ✅ Rate limiting (5 محاولات max) موجود في كل الموديولات
- ✅ Expiry mechanism (5 دقائق) موجود
- ✅ Context binding (ip + session) موجود
- ✅ `secret.key` مستثنى من `.gitignore`
- ✅ DB permissions مضبوطة على `0o600`
- ✅ Cleanup لـ expired entries موجود
- ✅ Event logging شامل ومنظم

---

*Report generated by automated code analysis + manual expert review*  
*InnoCaptcha devmode branch — commit HEAD*
