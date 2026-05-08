# تقرير تدقيق أمني وبرمجي لمكتبة InnoCaptcha (فرع `devmode`)

## نظرة عامة
مكتبة InnoCaptcha هي مكتبة بايثون احترافية لتوليد وفحص كلمات التحقق (CAPTCHA) بأنواع متعددة (نصية، رياضية، صوتية، صورية، وتعرف على الكلام). تعتمد المكتبة على قاعدة بيانات SQLite لتخزين التحديات، وتستخدم تشفير Fernet لحماية الإجابات، مع ميزات أمان مثل ربط التحدي بعنوان IP ومعرف الجلسة، وتحديد عدد المحاولات، وانتهاء الصلاحية التلقائي.

**الملفات التي تم فحصها:**
- `__init__.py` - تعريف الإصدار والاستيرادات.
- `utils.py` - أدوات مساعدة (قاعدة البيانات، التسجيل، التشفير).
- `text.py` - فئة TextCaptcha.
- `math.py` - فئة MathCaptcha.
- `audio.py` - فئة AudioCaptcha (ملف غير مكتمل/مشوه).
- `image.py` - فئة ImageCaptcha (لم يتم تحميله بعد).
- `voice.py` - فئة VoiceCaptcha (لم يتم تحميله بعد).
- `cli.py` - واجهة سطر أوامر (لم يتم تحميله بعد).

---

## 1. ثغرات أمنية محتملة

### 1.1. **SQL Injection عبر أسماء الجداول (خطورة منخفضة)**
- **الملف:** `utils.py`
- **الوصف:** تستخدم الدالة `DB._initialize_schema()` استعلامات SQL ديناميكية مع أسماء جداول من القائمة `ALLOWED_TABLES`. على الرغم من أن هذه القائمة ثابتة ومحددة مسبقًا (`{'text', 'audio', 'math', 'voice', 'image'}`)، إلا أن أي توسع مستقبلي أو خطأ في التكوين قد يسمح بحقن SQL إذا تم تمرير أسماء جداول من مصدر خارجي دون تحقق.
  ```python
  for table in ALLOWED_TABLES:
      self.cursor.execute(f"""CREATE TABLE IF NOT EXISTS {table} (...)""")
```

· التوصية:
  · استخدام تحقق صارم من أسماء الجداول قبل إدراجها في الاستعلامات.
  · الاعتماد على استعلامات مُعدّة (prepared statements) حتى في عمليات DDL.

1.2. استخدام استعلامات ديناميكية في عمليات الحذف (خطورة منخفضة)

· الملفات: text.py, math.py, audio.py (بافتراض نمط موحد)
· الوصف: في دوال verify يتم استخدام استعلامات SQL ديناميكية مثل:
  ```python
  db.execute("DELETE FROM text WHERE id = ?", (self.id,))
  ```
  بينما يتم استخدام استعلامات معاملات (parameterized queries) للمعاملات، ولكن في حالة audio.py (الملف المشوه) قد يكون هناك استعلامات غير آمنة. لا يمكن تأكيد ذلك بسبب عدم اكتمال الملف.
· التوصية: التأكد من أن جميع استعلامات SQL تستخدم معاملات مرتبطة (bound parameters) وليس التلاعب بالنصوص.

1.3. تخزين المفتاح السري في ملف داخل المشروع (خطورة متوسطة)

· الملف: utils.py
· الوصف: الدالة get_encryption_key() تبحث عن المفتاح إما في متغير البيئة INNOCAPTCHA_KEY أو في ملف data/secret.key. إذا لم يوجد أي منهما، تقوم الدالة بإنشاء مفتاح جديد وحفظه في data/secret.key بصلاحيات 0o600. تضمين ملف مفتاح سري داخل مستودع الكود يعد ممارسة غير آمنة، على الرغم من أن الملف قد لا يكون مرفوعًا إلى Git (يجب التأكد من وجوده في .gitignore).
· التوصية:
  · إزالة ملف secret.key نهائيًا من المستودع.
  · الاعتماد حصريًا على متغير البيئة.
  · إضافة تحذير واضح في التوثيق بعدم رفع المفتاح إلى أنظمة التحكم بالإصدار.

1.4. عدم التحقق من سلامة المفتاح (خطورة منخفضة)

· الملف: utils.py
· الوصف: الدالة get_encryption_key() لا تتحقق من صلاحية المفتاح (مثلاً، هل هو مفتاح Fernet سليم). إذا تم تعيين مفتاح غير صالح، ستفشل عمليات التشفير لاحقًا.
· التوصية: إضافة تحقق من نوع المفتاح (يجب أن يكون bytes بطول 32 بايت ومشفر base64) قبل استخدامه.

1.5. هجمات التوقيت (Timing Attacks) - تمت معالجتها جزئيًا

· الملفات: text.py, math.py, audio.py
· الوصف: تستخدم المقارنات secrets.compare_digest() لمقارنة المدخلات، وهو صحيح. ولكن التحقق من تطابق IP ومعرف الجلسة يستخدم secrets.compare_digest فقط إذا كانت القيمة المخزنة غير فارغة.
  ```python
  ip_match = not db_ip or secrets.compare_digest(db_ip, ip or "")
  ```
  إذا كان db_ip فارغًا، فإن ip_match ستكون True دون مقارنة، مما قد يسمح بتجاوز فحص الربط (binding) في حالات معينة.
· التوصية: التأكد من أن جميع الفحوصات الأمنية تستخدم مقارنات آمنة دائمًا، وعدم السماح بوجود قيم فارغة في الحقول الأمنية.

1.6. إمكانية تخمين معرّفات التحديات (Challenge IDs)

· الملفات: جميع الفئات
· الوصف: يتم توليد معرّفات التحديات باستخدام secrets.token_hex(16) مما ينتج 32 حرفًا سداسيًا عشوائيًا. هذا آمن. لكن يجب التأكد من عدم إمكانية تخمينها.

---

2. مشاكل برمجية وهيكلية

2.1. ملف audio.py غير مكتمل أو تالف

· الوصف: محتوى الملف الذي تم استرداده يبدو مقتطعًا وغير مكتمل. يحتوي على كود غير متناسق مع أخطاء في تركيب الجمل. هذا يشير إلى مشكلة في الرفع أو تلف في الملف.
· التوصية: إعادة رفع الملف الصحيح الكامل، والتأكد من عدم وجود أخطاء في تحويل النص.

2.2. عدم وجود اختبارات وحدة (Unit Tests)

· الوصف: لم يتم العثور على مجلد tests/ أو ملفات اختبار. مكتبة بهذا الحجم الأمني الحساس تحتاج إلى تغطية اختبارية شاملة.
· التوصية: إنشاء مجموعة اختبارات آلية تغطي:
  · إنشاء كل نوع من أنواع CAPTCHA.
  · التحقق من الإجابات الصحيحة والخاطئة.
  · اختبارات أمان (تجاوز عدد المحاولات، انتهاء الصلاحية، ربط IP).
  · اختبارات اختراق (SQL injection، timing attacks).

2.3. تكرار الكود (Code Duplication)

· الوصف: دوال verify في text.py وmath.py وaudio.py تحتوي على نفس المنطق تقريبًا مع اختلاف اسم الجدول فقط.
· التوصية: إعادة هيكلة الكود باستخدام قالب موحد (Base class) لتقليل التكرار وتسهيل الصيانة.

2.4. استخدام exec أو eval؟

· الوصف: في math.py يتم تجنب eval() صراحة، ولكن يتم استخدام قاموس operators لتنفيذ العمليات الحسابية، وهو آمن.
  ```python
  operators = {"+": operator.add, "-": operator.sub, "×": operator.mul}
  ```
· التوصية: الاستمرار في هذا النهج.

2.5. عدم وجود معالجة استثنائية موحدة

· الملفات: جميع الفئات
· الوصف: دوال verify تعيد قيمًا مختلفة (True, False, نصوص). هذا غير متناسق ويصعب على المستهلك التعامل معها.
· التوصية: استخدام إرجاع قيم موحدة (مثلاً، True/False) مع رفع استثناءات محددة للحالات الاستثنائية (مثل "غير موجود"، "منتهي الصلاحية").

2.6. عدم تنظيف التحديات منتهية الصلاحية بشكل دوري

· الوصف: يتم استدعاء cleanup() فقط عند إنشاء تحدي جديد. إذا لم يتم إنشاء تحديات جديدة لفترة، قد تتراكم البيانات القديمة.
· التوصية: إضافة آلية تنظيف خلفية دورية (مثلاً عبر threading.Timer أو جدولة).

---

3. توصيات أمنية عامة

· تشفير البيانات في السكون (Encryption at Rest): يتم تشفير الإجابات باستخدام Fernet، وهذا جيد. لكن يجب التأكد من أن المفتاح لا يتم تبادله عبر قنوات غير آمنة.
· تسجيل الأحداث: استخدام log_event جيد، ولكن تأكد من عدم تسجيل بيانات حساسة (مثل الإجابات الصحيحة) حتى في السجلات.
· حماية ضد هجمات CSRF: إذا تم استخدام المكتبة في سياق ويب، يجب تنفيذ حماية ضد CSRF عند إرسال التحديات.
· استخدام HTTPS: ينبغي توثيق ضرورة استخدام HTTPS في الإنتاج لمنع اعتراض التحديات.
· تحديث التبعيات: التأكد من تحديث المكتبات مثل cryptography, Pillow وغيرها لتفادي ثغراتها.

---

4. توصيات تطويرية

المجال التوصية
التوثيق إضافة أمثلة شاملة لتكامل الويب، وإعدادات الإنتاج، وتوجيهات الأمان.
الاختبارات بناء هيكل اختبارات شامل (unit, integration, security).
CI/CD إعداد خط أنابيب تكامل مستمر مع فحوصات أمان تلقائية (مثل Bandit, Safety).
دعم قواعد بيانات أخرى توفير خيارات تخزين إضافية مثل PostgreSQL أو Redis.
دعم مخصص للويب إنشاء إضافات جاهزة لأطر العمل مثل Flask, Django.
تدويل (i18n) دعم كامل للغات متعددة مع ملفات ترجمة.

---

5. خلاصة

المكتبة تظهر تصميمًا أمنيًا واعيًا في جوانب عدة، ولكن توجد بعض النقاط التي تحتاج إلى معالجة عاجلة، خاصةً فيما يتعلق بإدارة المفاتيح وسلامة الملفات. يُنصح بإجراء تدقيق أمني متعمق يشمل جميع الأنواع خاصةً VoiceCaptcha وImageCaptcha فور الانتهاء من رفع الملفات الصحيحة.

ملاحظة: لم يتم تحليل ملفات image.py, voice.py, cli.py بشكل كامل بسبب عدم توفرها في الوقت الحالي. يُرجى تحديث التقرير بعد فحصها.

```# تقرير مراجعة أمنية وهندسية لمكتبة [InnoCaptcha](https://github.com/InnoSoft-Company/InnoCaptcha) — فرع [devmode](https://github.com/InnoSoft-Company/InnoCaptcha/tree/devmode)

**نطاق المراجعة:** الكود الموجود على فرع `devmode` عند أحدث HEAD ظاهر أثناء الفحص (`195dd4c`).

**نوع التقرير:** Security + Reliability + Packaging + CI/CD + DX audit.

**ماذا تم التحقق منه عمليًا؟**
تمت مراجعة الملفات الأساسية، تشغيل فحوصات static analysis محليًا، تجربة بناء الحزمة، والتأكد من سلوكيات مهمة مثل استيراد الحزمة وباندل الملفات داخل الـ wheel. النتيجة: عند بناء الحزمة، تم تضمين `secret.key` و`captcha.db` وملف log داخل الـ wheel، كما أن `import InnoCaptcha` فشل في بيئة لا تحتوي كل الاعتمادات الاختيارية، وهذا يؤكد وجود مشاكل تشغيلية وسلاسل توريد حقيقية.

---

## الملخص التنفيذي

المكتبة فيها شغل محترم في نقاط معينة: استخدام `secrets.compare_digest`، وتشفير الإجابات، وفكرة ربط التحقق بـ IP / session، وفصل الأنواع المختلفة للكابتشا. لكن في المقابل، الفرع الحالي فيه **مشكلات كبيرة جدًا** في **إدارة الأسرار**، و**باندل ملفات حساسة داخل الحزمة**، و**بنية import/dependencies**، و**منظومة CI/CD**. أخطر نقطة عندي ليست فقط ثغرة runtime واحدة، بل إن **سلسلة التوزيع بالكامل** ممكن تخرج للمستخدم النهائي بمفتاح مشفّر ثابت وملفات قاعدة بيانات ولوجات متضمَّنة داخل الـ package. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L25-L38)

الأولوية القصوى عندي: **إيقاف شحن `secret.key` و`captcha.db` و`logs/` داخل الحزمة فورًا**، ثم **فصل dependencies الثقيلة والاختيارية**، ثم **إصلاح الـ CI/CD** لأن الـ pipeline الحالي ممكن يعطيك إحساس زائف بالأمان أو ينشر نسخة على PyPI في توقيت غير مقصود. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L38-L45) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L26-L29) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml#L25-L34) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/pypi.yml#L1-L39)

---

## تصنيف سريع للمخاطر

| المستوى | العدد | ملاحظات |
|---|---:|---|
| Critical | 1 | إدارة الأسرار والـ packaging الحاليين يخلقوا خطر supply-chain وتسريب artifacts |
| High | 5 | bypass محتمل، import architecture سيئة، CI/CD غير موثوق، نشر غير منضبط |
| Medium | 7 | خصوصية، لوجات، مسارات تخزين، الاعتمادات، helper scripts، CodeQL automation |
| Low | 3 | تناقضات policy/test/style/legal hygiene |

---

## أهم النتائج بالتفصيل

### 1) 🔥 Critical — مفتاح التشفير fallback داخل الحزمة + شحن ملفات حساسة داخل الـ package

الدالة `get_encryption_key()` تبحث أولًا عن `INNOCAPTCHA_KEY`، لكن لو غير موجود ترجع لمفتاح مخزَّن في `InnoCaptcha/data/secret.key`، وإن لم يوجد تنشئه هناك داخل package directory نفسه. هذا وحده سيّئ تشغيلًا وأمنيًا، لكن الأسوأ أن `pyproject.toml` و`setup.py` يفعّلان packaging واسع جدًا (`InnoCaptcha = ["**/*"]` و `package_data={"InnoCaptcha": ["**/*"]}`)، ومع `.gitignore` الحالي فالملفات الحساسة أصلًا متتبعة داخل المستودع. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L25-L38) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L38-L45) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L26-L29) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.gitignore#L1-L6)

**المشكلة العملية المؤكدة:** أثناء البناء المحلي للـ wheel تم تضمين:
- `InnoCaptcha/data/secret.key`
- `InnoCaptcha/data/dbs/captcha.db`
- `InnoCaptcha/data/logs/innocaptcha_2026-05-06.log`
- بالإضافة إلى موديل `yolo11n.pt`

والملفات نفسها موجودة بالفعل في المستودع: [`secret.key`](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/data/secret.key)، [`captcha.db`](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/data/dbs/captcha.db)، [`log`](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/data/logs/innocaptcha_2026-05-06.log).

**الأثر:**
- أي مستخدم قد يستعمل fallback key بدل مفتاح deployment خاص به.
- تسريب runtime artifacts مع الحزمة.
- خطر supply-chain حقيقي لأن artifact النهائي يحمل بيانات لا يجب شحنها أصلًا.
- صعوبة rotation ونقل المسؤولية الأمنية للمستخدم النهائي بدون وعيه.

**الإصلاح المقترح:**
1. حذف `secret.key` و`captcha.db` و`logs/` من المستودع ومن الـ wheel فورًا.
2. منع أي fallback إلى key داخل package.
3. جعل `INNOCAPTCHA_KEY` **إجباريًا في production** مع validation صريح.
4. إنشاء storage خارجي configurable بدل الكتابة داخل package dir.
5. عمل key rotation لو المفتاح الحالي استُخدم خارج التطوير.

---

### 2) 🚨 High — `import InnoCaptcha` يفشل لو الاعتمادات الاختيارية غير متاحة

الملف `__init__.py` يعمل eager import لكل الأنواع دفعة واحدة: text/audio/math/voice/image. هذا يجعل مجرد `import InnoCaptcha` محتاج كل dependencies الثقيلة والاختيارية حتى لو المستخدم لا يريد إلا TextCaptcha فقط. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/__init__.py#L1-L7)

وفوق هذا، `image.py` يعمل import مباشر لـ `ultralytics`, و`text.py` يعتمد على `bidi` و`arabic_reshaper`, و`voice.py` يعتمد على `speech_recognition` و`pydub`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L1-L16) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L1-L18) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L1-L5)

**التحقق العملي:** الاستيراد فشل محليًا مباشرة بسبب `ModuleNotFoundError`، وهذا يؤكد أن بنية الحزمة الحالية brittle جدًا.

**الأثر:**
- DX سيئة جدًا.
- أي deployment بسيط سيتكسر حتى لو لا يستخدم image/voice.
- تضخيم install footprint بلا داعٍ.

**الإصلاح المقترح:**
- Lazy imports داخل `__init__.py` أو إزالة eager exports.
- تقسيم extras مثل:
  - `pip install InnoCaptcha[text]`
  - `pip install InnoCaptcha[voice]`
  - `pip install InnoCaptcha[image]`
- توثيق dependencies الأساسية مقابل الاختيارية بوضوح. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L30-L45)

---

### 3) 🚨 High — احتمال bypass في `ImageCaptcha` لو الموديل لم يكتشف أي شيء

في `create()` يتم تكوين `correct_grids` من الـ detections. لو الموديل لم يُرجع أي detection مطابق، فالإجابة تصبح string فارغ `""`. لاحقًا في `verify()` يتم تطبيع إدخال المستخدم ثم مقارنته مباشرة بالإجابة المخزنة. هذا يعني أن challenge بدون detections قد يُقبل بإجابة فارغة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L65-L76) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L120-L123)

**الأثر:**
- Fail-open behavior.
- bypass محتمل للكابتشا في حالات miss detection.
- كلما ضعفت دقة الموديل أو quality الصورة، زادت الخطورة.

**الإصلاح المقترح:**
- لو `correct_grids` فاضية: regenerate challenge أو fail closed.
- تطبيق حد أدنى للـ confidence.
- رفض أي challenge ليس له answer صالح non-empty.
- إضافة test يغطي no-detection path.

---

### 4) 🚨 High — الـ release pipeline ممكن ينشر PyPI في وقت غير مقصود

Workflow تحديث README يشتغل بعد نجاح CodeQL ويضيف timestamp إلى `README.md` ثم يعمل commit وpush مباشرة على الفرع. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/readme-workflow.yml#L1-L27)

وفي نفس الوقت، Workflow النشر على PyPI مضبوط ليتفعّل بعد اكتمال workflow اسمه `Update README After CodeQL` بنجاح، أو عند الـ tags. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/pypi.yml#L1-L39)

**الأثر:**
- نجاح CodeQL قد يقود لسلسلة: تعديل README → push → publish.
- النشر غير مربوط بإصدار release واضح أو approval gate.
- أي خطأ في README workflow أو misfire قد يسبب churn أو release accidental.

**الإصلاح المقترح:**
- النشر يكون من tags/releases فقط.
- حذف auto-commit على README أو تحويله إلى PR منفصل.
- إضافة environment protection / manual approval قبل PyPI publish.

---

### 5) 🚨 High — الـ CI الحالي يعطي false green ولا يختبر المكتبة فعليًا

الـ workflow الخاص بـ CI يثبت `flake8` و`pytest` فقط، ثم يثبت `requirements.txt` **إن وجد**. لكن المشروع أصلًا لا يحتوي `requirements.txt` حاليًا، والاعتمادات معرفة في `pyproject.toml`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml#L25-L28) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L30-L45)

ثم يتم تشغيل `pytest InnoCaptcha --maxfail=5 --disable-warnings -q || true`، أي حتى لو الاختبارات فشلت فالـ pipeline سيكمل. والأسوأ أن `pytest InnoCaptcha` لا يستهدف ملف الاختبارات الرئيسي `test_innocaptcha.py` أصلًا بشكل واضح. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml#L35-L37) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/test_innocaptcha.py#L1-L168)

**الأثر:**
- regressions تعدّي بدون ما تتكشف.
- الإحساس بالأمان هنا misleading.
- Security fixes ممكن تتكسر والـ badge يفضل أخضر.

**الإصلاح المقترح:**
- `pip install -e .` أو `python -m pip install .[test]`.
- تشغيل `pytest -q` بدون `|| true`.
- إضافة matrix تشمل 3.12 أيضًا.
- فصل smoke tests عن integration tests.

---

### 6) 🚨 High — إدارة الأسرار المعلنة في README لا تطابق السلوك الفعلي

الـ README يقول للمستخدم في production يضبط `INNOCAPTCHA_KEY`، لكن الكود لا يفرض ذلك فعليًا؛ بل يسكت ويرجع لمفتاح ملفي fallback. هذا تناقض خطير بين **الوثائق** و**السلوك الحقيقي**. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/README.md#L43-L47) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L25-L38)

**الأثر:**
- المطور يفتكر أنه آمن لأنه قرأ README.
- بينما التطبيق قد يعمل بمفتاح ثابت داخل package بدون ما يعرف.

**الإصلاح المقترح:**
- لو env var غير موجود في production mode: ارفع exception واضحة.
- أضف health check يوضح حالة key management.

---

### 7) ⚠️ Medium — `CodeQL` automation الحالية تبدو brittle جدًا وقد تكون broken

في خطوة `Create Super Super Issues` يتم استدعاء GitHub API عبر `curl` باستخدام `$GITHUB_TOKEN` داخل shell script بدون env mapping ظاهر في الخطوة نفسها، ثم استخدام `jq '.alerts // []'` على response قد لا يكون بهذا الشكل أصلًا، وبعدها `gh issue create` بدون setup auth واضح. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/codeql.yml#L29-L57)

**الأثر:**
- فشل صامت أو noisy.
- issue spam أو duplication.
- automation غير موثوق.

**الإصلاح المقترح:**
- استخدام `actions/github-script` أو REST call صحيح ببنية response مضمونة.
- تمرير auth بشكل explicit.
- dedupe بناءً على alert number/state وليس title فقط.

---

### 8) ⚠️ Medium — `VoiceCaptcha` يرسل/يعتمد على خدمة خارجية للتعرف على الصوت

التحقق في `VoiceCaptcha` يعتمد على `recognize_google()` بشكل مباشر. هذا يخلق dependence على خدمة خارجية، ويطرح أسئلة خصوصية وavailability، ويجعل الاختبارات reproducibility أقل. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L85-L105)

**الأثر:**
- بيانات صوت المستخدم قد تخرج لجهة خارجية.
- فشل الشبكة = فشل التحقق.
- سلوك غير deterministic.

**الإصلاح المقترح:**
- اجعل الـ STT backend قابلًا للحقن/الاستبدال.
- أضف offline mode أو provider abstraction.
- وثّق privacy implications بوضوح.

---

### 9) ⚠️ Medium — اللوجات تسجل بيانات حساسة نسبيًا داخل package directory

الـ modules تسجل `ip` و`session` وcaptcha IDs في اللوجات عبر `log_event()`، ومكان اللوجات نفسه هو `InnoCaptcha/data/logs`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L16-L23) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L58-L58) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L48-L48) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L51-L51) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L79-L79)

**الأثر:**
- privacy risk.
- logs قابلة للدخول في package artifact مثلما حصل فعليًا.
- كتابة داخل site-packages قد تسبب مشاكل permissions.

**الإصلاح المقترح:**
- عدم log للـ session/IP بصيغتهما الخام.
- hashing / truncation / configurable redaction.
- نقل اللوجات إلى مسار external configurable.

---

### 10) ⚠️ Medium — تخزين runtime state داخل package directory تصميميًا غير مناسب

قاعدة البيانات واللوجات والمفتاح كلها موجهة داخل `BASE_DIR/data/...`، أي داخل مجلد المكتبة نفسها. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L5-L13)

**الأثر:**
- مشاكل permissions في Docker / read-only filesystems / system installs.
- اختلاط كود التوزيع مع runtime state.
- صعوبة التشغيل multi-instance.

**الإصلاح المقترح:**
- دعم storage backend قابل للتهيئة.
- استخدام `appdirs/platformdirs` أو path يحدده المستخدم.
- دعم external DB أو memory backend.

---

### 11) ⚠️ Medium — الاعتمادات ثقيلة وغير مفصولة وغير pinned

كل الاعتمادات في `pyproject.toml` و`setup.py` معرفة كـ runtime dependencies مباشرة، ومنها `ultralytics`, `opencv-python`, `scipy`, `SpeechRecognition`, `pydub`, `arabic-reshaper`, `python-bidi`. لا يوجد extras ولا حدود versions واضحة ولا constraints file. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L30-L45) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L31-L43)

**الأثر:**
- drift في السلسلة البرمجية.
- install ثقيل جدًا على مستخدم يريد text/audio فقط.
- reproducibility ضعيفة.

**الإصلاح المقترح:**
- تقسيم extras.
- تحديد lower/upper bounds.
- إضافة lock/constraints strategy وDependabot/Renovate.

---

### 12) ⚠️ Medium — `UploadToGitHub.py` فيه command injection risk و`force push`

السكريبت يستخدم `os.system()` مع commit message يدخل فيه user input، وفي النهاية يعمل `git push ... --force`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/UploadToGitHub.py#L7-L22)

**الأثر:**
- تعريض بيئة المطور local shell injection.
- overwrite للتاريخ عبر force push.
- masking للأخطاء بسبب `except: pass`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/UploadToGitHub.py#L7-L13)

**الإصلاح المقترح:**
- استبدال `os.system` بـ `subprocess.run([...], check=True)`.
- sanitization للمدخلات.
- حذف `--force` إلا في حالات محكومة جدًا.
- إزالة `except: pass`.

---

### 13) ⚠️ Medium — `ImageCaptcha` يستخدم matching heuristic فضفاض

الشرط التالي يسمح بالمطابقة إذا كان اسم class المكتشف يساوي الهدف أو أحدهما substring من الآخر:

```python
if det_cls == target_cls or det_cls in target_cls or target_cls in det_cls:
```

وهذا قد ينتج false positives حسب أسماء الكلاسات. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L43-L49)

**الأثر:**
- قبول grids غير دقيقة.
- challenge quality متقلبة.

**الإصلاح المقترح:**
- مطابقة exact label فقط أو alias map واضحة.
- إضافة confidence threshold واختبارات dataset-specific.

---

### 14) ⚠️ Medium — لا يوجد توثيق licenses/attribution واضح للأصول المضمّنة

المشروع يضم خطوطًا وصوتيات وصورًا وموديلًا داخل `data/`، لكن لا يظهر في المستودع سوى `LICENSE` واحد للمشروع نفسه، بدون third-party notices واضحة للأصول المضمّنة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/tree/devmode/InnoCaptcha/data) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/LICENSE)

**الأثر:**
- legal/compliance risk.
- صعوبة إعادة التوزيع بثقة.

**الإصلاح المقترح:**
- إنشاء `THIRD_PARTY_LICENSES.md`.
- توثيق مصدر وترخيص كل font/audio/image/model.

---

### 15) ⚠️ Medium — قاعدة البيانات المضمَّنة تحتوي rows فعلية وآثار schema قديمة

أثناء الفحص المحلي، ملف `InnoCaptcha/data/dbs/captcha.db` لم يكن فارغًا، واحتوى rows فعلية في جداول مثل `text`, `math`, `audio`، كما ظهرت جداول إضافية مثل `event_log` و`encryption_key` لا تتطابق مع schema الحالية في `_initialize_schema()`. schema الفعلية التي ينشئها الكود الحالي تقتصر على `text/audio/math/voice/image`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L57-L80)

**الأثر:**
- repository hygiene ضعيفة.
- migration story غير واضحة.
- احتمال ارتباك أو bugs في upgrades.

**الإصلاح المقترح:**
- لا تشحن DB أصلًا.
- استخدم migrations صريحة.
- وفر init command ينشئ DB نظيفة عند التشغيل.

---

### 16) 🟡 Low — سياسة الأمان لا تطابق النسخة الحالية

`SECURITY.md` يقول إن `3.0.x` فقط مدعوم أمنيًا، بينما `pyproject.toml` و`setup.py` و`__init__.py` تشير إلى `2.4.0`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/SECURITY.md#L5-L9) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L5-L8) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L4-L5) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/__init__.py#L7-L7)

**الأثر:**
- trust/confusion.
- المستخدم لا يعرف هل النسخة الحالية تتلقى إصلاحات أم لا.

**الإصلاح المقترح:**
- تحديث policy فورًا وربطها بفرع/إصدار فعلي.

---

### 17) 🟡 Low — التغطية الاختبارية غير كافية، وفيها `eval()` داخل الاختبارات

الاختبارات الحالية لا تغطي voice/image بشكل end-to-end حقيقي، وفي `MathCaptcha` test يوجد `eval(q)` داخل ملف الاختبار. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/test_innocaptcha.py#L140-L166)

**الأثر:**
- مشاكل مهمة قد تمر بدون كشف.
- test hygiene أضعف من المطلوب لمكتبة security-sensitive.

**الإصلاح المقترح:**
- mocks للـ STT والـ YOLO.
- property tests للـ normalization والـ expiry والـ attempts.
- إزالة `eval` حتى من الاختبارات.

---

### 18) 🟡 Low — debt كبير في style/maintainability

الفحص المحلي بـ `flake8` أظهر عددًا كبيرًا جدًا من مشاكل style/formatting/import hygiene وunused imports وbare excepts. هذا ليس vulnerability مباشرة، لكنه يزيد احتمالية bugs ويصعّب المراجعة الأمنية.

**الإصلاح المقترح:**
- `ruff` أو `flake8 + black + isort`.
- منع merge لو lint/test فشلوا.
- تقليل الأسطر الطويلة وتوحيد indentation.

---

## ملاحظات إيجابية

رغم المشاكل السابقة، في نقاط جيدة ومفيدة فعلًا: استخدام `secrets.token_hex`، و`compare_digest` للمقارنة، وعدم استخدام `eval()` داخل منطق math الحقيقي، وفكرة حذف التحدي بعد النجاح، وفكرة attempt limits/expiry نفسها جيدة كأساس معماري. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L49-L58) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L126-L154) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/math.py#L121-L136) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L99-L124)

المعنى هنا: المشروع **قابل جدًا للتحسن**، لكن محتاج إعادة ترتيب الأولويات الأمنية والـ packaging والـ release discipline قبل أي claims إضافية عن “production-ready”.

---

## خطة إصلاح مقترحة حسب الأولوية

### خلال 24 ساعة

| أولوية | المطلوب |
|---|---|
| P0 | إزالة `secret.key`, `captcha.db`, `logs/` من Git ومن الـ wheel |
| P0 | وقف PyPI publish التلقائي المرتبط بنجاح CodeQL/README |
| P0 | إصلاح `ImageCaptcha` ليعمل fail-closed لو لا توجد detections |
| P0 | إزالة `|| true` من pytest وإصلاح install في CI |
| P1 | حذف `UploadToGitHub.py` أو عزله عن الريبو العام |

### خلال أسبوع

| أولوية | المطلوب |
|---|---|
| P1 | تحويل dependencies إلى extras وتطبيق lazy imports |
| P1 | نقل storage/log/key paths إلى config خارجي |
| P1 | إضافة tests حقيقية لـ image/voice مع mocks |
| P1 | توثيق licenses للأصول المضمّنة |

### خلال شهر

| أولوية | المطلوب |
|---|---|
| P2 | تصميم storage backend abstraction |
| P2 | بناء release pipeline قائم على tags + approvals |
| P2 | threat model رسمي للمكتبة |
| P2 | privacy mode للـ logs والـ voice backends |
---

## التقييم النهائي

**الحالة الحالية:** لا أنصح باعتبار الفرع الحالي production-ready بدون إصلاحات سريعة، خصوصًا بسبب إدارة الأسرار والـ packaging والـ CI/CD.

**درجة المخاطرة العامة:** **8.5 / 10**

**لو سأرتب الإصلاحات بيدٍ واحدة:**
1. Secret/package cleanup
2. ImageCaptcha fail-closed
3. CI/CD and release pipeline
4. Optional dependency architecture
5. Privacy/logging/storage redesign

---

## روابط مرجعية مباشرة

- الكود الأساسي: [InnoCaptcha package](https://github.com/InnoSoft-Company/InnoCaptcha/tree/devmode/InnoCaptcha)
- إدارة التخزين والمفتاح: [utils.py](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py)
- صورة الكابتشا بالـ YOLO: [image.py](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py)
- التحقق الصوتي: [voice.py](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py)
- الاعتمادات: [pyproject.toml](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml)
- التغليف: [setup.py](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py)
- CI: [python-package.yml](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml)
- CodeQL: [codeql.yml](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/codeql.yml)
- README auto-update: [readme-workflow.yml](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/readme-workflow.yml)
- PyPI publish: [pypi.yml](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/pypi.yml)
- أداة الرفع المحلية: [UploadToGitHub.py](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/UploadToGitHub.py)
- سياسة الأمان: [SECURITY.md](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/SECURITY.md)