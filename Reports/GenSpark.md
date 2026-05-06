# تقرير مراجعة أمنية وهندسية لمشروع [InnoCaptcha](https://github.com/InnoSoft-Company/InnoCaptcha)

- **الفرع:** `devmode`
- **الـ commit المُراجع:** `cd705ab75b344d4fd4147e1ff757f1771fc1e1b6`
- **نوع المراجعة:** مراجعة كود + تشغيل اختبارات + فحص التغليف وCI/CD
- **ملخص سريع:** المكتبة فيها أفكار كويسة، لكن في حالتها الحالية لا أعتبرها جاهزة كـ CAPTCHA library production-grade؛ لأن فيها مشاكل أمنية ووظيفية وتشغيلية مؤثرة، وبعضها يضرب الادعاءات الأمنية المذكورة في README بشكل مباشر.

---

## الملخص التنفيذي

أخطر المشاكل الحالية هي: إمكانية تجاوز ربط الـ IP/Session بسهولة، شحن قاعدة بيانات SQLite جاهزة داخل الحزمة ومعها مفاتيح تشفير وبيانات تشغيلية، كسر منطق `VoiceCaptcha` لأنه يشفّر الجملة داخل `self.phrase` بدون API لإرجاع النص للمستخدم، ومنطق `ImageCaptcha` الذي يحسب الإجابة من **كل** الـ detections وليس من الفئة المطلوبة فقط. بالإضافة إلى ذلك، الـ workflows الحالية قد تعمل حلقة أوتوماتيكية بين CodeQL وREADME والنشر على PyPI، والاختبارات الحالية لا تحميك لأن الـ CI متساهل جدًا ويتجاهل الفشل. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L122-L146) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L24-L61) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L38-L54) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L31-L73) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/readme-workflow.yml#L1-L31) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/pypi.yml#L1-L59)

أثناء التشغيل العملي للمشروع محليًا، الاختبارات الحالية فشلت بشكل واضح (`4 failed, 8 errors`)، ونتيجة `flake8` أظهرت عددًا كبيرًا جدًا من المخالفات الأسلوبية والهيكلية، كما أن الـ wheel/SDist الناتجين يحملان ملفات `__pycache__` وقاعدة البيانات وملفات الموديل والبيانات داخل الحزمة. هذا يؤكد أن المشكلة ليست نظرية فقط، بل موجودة فعليًا في سلوك المشروع الحالي.

---

## 1) المشاكل الحرجة (Critical)

### 1.1 تجاوز ربط الـ IP / Session سهل جدًا

في كل دوال `verify` تقريبًا، التحقق من السياق مكتوب بالشكل التالي: يتم رفض الطلب **فقط لو** كان `ip` أو `session_id` مُرسَلين وتمت ملاحظة اختلافهما. هذا معناه أنه لو تم إنشاء التحدي مع `ip/session` ثم جاء التحقق **بدون** تمرير هذه القيم أصلًا، فلن يحدث رفض، وبالتالي ميزة الربط الأمني تصبح اختيارية ويمكن تجاوزها بسهولة. هذا ينسف الادعاء الأمني المذكور في README لأن الربط ليس إلزاميًا وقت التحقق. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L104-L106) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L132-L135) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/math.py#L179-L181) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L97-L100) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L76-L79) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/README.md#L25-L31)

**الاقتراح:** لو تم تخزين `ip_address` أو `session_id` مع التحدي، يجب أن يكون تمريرهما في `verify` إلزاميًا، ويُرفض الطلب لو كانت القيمة المخزنة موجودة لكن المدخلة `None` أو مختلفة. والأفضل إرجاع خطأ structured واضح بدل النصوص الحرة.

### 1.2 شحن قاعدة بيانات SQLite جاهزة داخل الحزمة مع مفاتيح تشفير وبيانات تشغيلية

المشروع يحدد `DB_PATH` داخل مجلد الحزمة نفسه (`InnoCaptcha/data/dbs/captcha.db`) ويقوم بإنشاء/استخدام قاعدة البيانات هناك مباشرة. هذا تصميم خطر جدًا لثلاثة أسباب: أولًا الحزمة تصبح stateful بدل أن تكون library نظيفة؛ ثانيًا في كثير من بيئات الإنتاج يكون `site-packages` غير قابل للكتابة؛ ثالثًا عند نشر الحزمة يتم شحن قاعدة البيانات نفسها داخل الـ artifacts، ما يعني شحن مفاتيح التشفير وأي سجلات/بيانات متبقية مع الحزمة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L5-L12) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L24-L61) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L38-L45)

**الاقتراح:** لا تشحن DB داخل الحزمة نهائيًا. انقل التخزين إلى مسار runtime configurable مثل `XDG_STATE_HOME` أو مسار يمرره المستخدم أو backend abstraction (SQLite/Postgres/Redis/In-memory). وفي الـ package data امنع إدراج `data/dbs/*` تمامًا.

### 1.3 جدول مفاتيح التشفير يسمح بأكثر من مفتاح والقراءة تتم بـ `LIMIT 1`

جدول `encryption_key` ليس فيه `PRIMARY KEY` أو قيد single-row، والكود يقرأ منه باستخدام `SELECT value FROM encryption_key limit 1`. هذا يعني أنه بمجرد وجود أكثر من مفتاح — سواء بسبب race condition أو تعبث محلي — يصبح فك التشفير غير موثوق، وقد يفشل عشوائيًا حسب الصف الذي عاد أولًا. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L55-L61) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L44-L49) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L54-L59)

**الاقتراح:** استخدم جدول إعدادات بمفتاح ثابت واحد، أو ملف secret خارجي، أو KMS/ENV variable. ولو ستبقى على SQLite، اجعل الجدول row واحدة فقط مع `CHECK(id = 1)` و`PRIMARY KEY` واضح.

### 1.4 `VoiceCaptcha` يكسر نفسه وظيفيًا بعد `create()`

داخل `VoiceCaptcha.create()` يتم وضع النص في `self.phrase` ثم يُشفَّر **داخل نفس المتغير** قبل الرجوع. النتيجة أن الكائن لا يحتفظ بالنص الواضح الذي يحتاجه التطبيق لإظهاره للمستخدم كي ينطقه. والأسوأ أنه لا توجد دالة public مثل `get_phrase()` ترجع العبارة الأصلية. بالتالي الموديول غير قابل للاستخدام الطبيعي إلا لو المستخدم أدخل عبارة بنفسه قبل التشفير. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L38-L54)

**الاقتراح:** احتفظ بالـ plaintext في متغير مؤقت منفصل للعرض، وخزن فقط النسخة المشفرة في قاعدة البيانات، وقدّم `get_phrase()` أو أرجع كائن challenge structured يحتوي `id` و`prompt`.

### 1.5 `ImageCaptcha` لا يتحقق من الفئة المطلوبة أصلًا

الكود يختار مجلدًا عشوائيًا مثل `cat` أو `dog` أو `stop sign` ويعتبره الهدف، لكنه عند حساب الإجابة لا يفلتر الـ detections على أساس الفئة المطلوبة. هو فقط يلف على كل `result.boxes.xyxy` ويحوّل أي bounding boxes موجودة إلى مربعات صحيحة. هذا معناه أن الإجابة تمثل “كل ما اكتشفه YOLO” وليس “المربعات التي تحتوي على الفئة المطلوبة”. وبالتالي الكابتشا قد تكون خاطئة أو غير قابلة للحل. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L20-L25) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L31-L60)

**الاقتراح:** استخدم `result.boxes.cls` وفلتر على class id المقابل للفئة المطلوبة مع confidence threshold واضح، واربط أسماء الفئات المحلية بأسماء فئات YOLO الرسمية، وأضف prompt عام مثل: “اختر المربعات التي تحتوي على قطط”.

### 1.6 لا يوجد API واضح لإرجاع prompt/target في `ImageCaptcha`

الكائن يختار `self.image_class` داخليًا، لكن لا توجد دالة مثل `get_prompt()` أو response object موحد يرسل للواجهة: `id + image + target class`. عمليًا المستهلك لازم يعتمد على خاصية داخلية undocumented، وده يضعف قابلية الاستخدام ويكسر الـ API contract. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L16-L29)

**الاقتراح:** قدّم API موحدة لجميع الأنواع مثل `create() -> Challenge(id, payload, prompt, expires_at)`.

### 1.7 الـ Workflows الحالية قد تسبب حلقة أوتوماتيكية ونشر غير منضبط

`CodeQL` يعمل على كل push، وبعد نجاحه Workflow آخر يفتح README ويضيف timestamp ثم يعمل commit + push. هذا الـ push يعيد تشغيل CodeQL مرة أخرى. ثم Workflow النشر على PyPI مضبوط أيضًا على `workflow_run` لنجاح تحديث README، ما قد يؤدي إلى نشر الحزمة بعد كل دورة نجاح بدل النشر المقصود فقط عند release/tag. هذه سلسلة أوتوماتيكية خطرة جدًا على نظافة المستودع وعلى سمعة الحزمة في PyPI. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/codeql.yml#L1-L33) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/readme-workflow.yml#L1-L25) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/pypi.yml#L1-L18)

**الاقتراح:** احذف Workflow تعديل README بالكامل أو اجعله يدويًا فقط، واجعل النشر على PyPI مقتصرًا على tags/release manual approval، وليس على `workflow_run`.

---

## 2) المشاكل العالية (High)

### 2.1 الاختبارات الحالية لا تمثل الكود الفعلي والـ CI يتجاهل الفشل

ملف الاختبارات قديم وغير متوافق مع السلوك الحالي: اختبارات `MathCaptcha` لا تستدعي `create()` أصلًا ثم تتوقع `question/answer` جاهزين، واختبارات `AudioCaptcha` تعتمد على `self.chars` رغم أن الكود يحذفها بعد `create()`, واختبارات `TextCaptcha` تتوقع تخزين الإجابة كنص واضح في DB بينما الكود يشفّرها إذا وجد مفتاح. فوق ذلك، الـ workflow الخاص بالـ Python package لا يثبت dependencies من `pyproject.toml`، ويشغّل pytest على مجلد `InnoCaptcha` بدل ملف الاختبار، ثم يضع `|| true` في النهاية فيتجاهل أي فشل. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/test_innocaptcha.py#L47-L165) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml#L33-L48) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L67-L71) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L52-L60)

**الاقتراح:** أعد كتابة الاختبارات من الصفر حول API حقيقي، واجعل CI يثبت الحزمة نفسها (`pip install .[test]` أو `pip install .`) ويُفشل الـ build عند أول test failure.

### 2.2 إنشاء Thread تنظيف لكل instance يفتح باب thread storm ومشاكل SQLite

في `TextCaptcha` و`AudioCaptcha` و`ImageCaptcha` و`VoiceCaptcha` يتم تشغيل `threading.Thread(target=self.cleanup, daemon=True).start()` في كل `__init__`. تحت ضغط حقيقي، كل request تقريبًا قد ينشئ thread جديدًا فقط لحذف سجلات منتهية، وهذا waste واضح للموارد وقد يزيد احتمالات `database is locked` مع SQLite. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L21-L39) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L20-L27) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L16-L29) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L24-L31)

**الاقتراح:** احذف الـ background thread من الـ instances. استخدم cleanup lazy كل X requests، أو scheduled job خارجي، أو SQL statement في بداية create/verify بدون threads.

### 2.3 كتابة الـ DB والـ logs داخل مجلد الحزمة ستفشل في بيئات كثيرة

المشروع ينشئ `data/dbs` و`data/logs` داخل مسار الحزمة نفسها. هذا قد يعمل على جهاز المطور، لكنه غالبًا لن يعمل جيدًا داخل Docker images المقفولة، أو serverless، أو عندما تكون الحزمة مثبتة بصلاحيات root لكن التشغيل بمستخدم عادي. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L5-L18)

**الاقتراح:** استخدم مسارات runtime خارج package directory، أو اسمح بحقن storage/logger backend.

### 2.4 `ImageCaptcha` يحمل موديل YOLO عند كل كائن جديد

في `__init__` يتم تحميل `YOLO(MODEL_PATH)` في كل مرة. هذا مكلف جدًا في الذاكرة والزمن، وسيصير bottleneck حقيقي في أي خدمة ويب. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L16-L20)

**الاقتراح:** استخدم singleton/cache للموديل على مستوى process أو dependency injection.

### 2.5 التحقق مربوط بالـ object state وليس challenge ID مستقل

كل `verify()` تعتمد على `self.id` الموجود داخل instance. هذا تصميم غير مناسب لتطبيقات الويب الحقيقية، لأن create وverify غالبًا يحدثان في requestين مختلفين وقد يمران عبر process مختلف. الكود يخزن الـ challenge في DB لكن لا يتيح API منطقية مثل `verify(captcha_id, answer, context)`؛ وبالتالي هو stateful بدون داع. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L110-L155) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L83-L125) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/math.py#L165-L197)

**الاقتراح:** افصل بين generator وverifier، واجعل التحقق يستقبل `captcha_id` صراحة.

### 2.6 `VoiceCaptcha` يعتمد على Google STT خارجي بدون توضيح الخصوصية أو fallback

التحقق الصوتي يرسل الصوت فعليًا لخدمة Google عبر `recognize_google`. هذا يخلق مخاطر availability وprivacy وcompliance، خاصة لو المكتبة ستستخدم في منتجات حقيقية أو مناطق تنظيمية حساسة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/voice.py#L87-L105)

**الاقتراح:** وثّق ذلك صراحة، واجعل الـ STT backend قابلًا للاستبدال، وقدّم offline/backend-agnostic interface.

---

## 3) المشاكل المتوسطة (Medium)

### 3.1 إدخال المستخدم لا يتم normalize بشكل كافٍ

`ImageCaptcha.verify()` يتطلب تطابقًا حرفيًا للنص مثل `1,2,5`؛ فلا يوجد trim للمسافات، ولا normalization للترتيب، ولا deduplication. هذا يضرب UX ويزيد false negatives. نفس الفكرة موجودة في مواضع أخرى بشكل متفاوت. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/image.py#L112-L121) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L146-L155)

**الاقتراح:** طبّع الإدخال قبل المقارنة: trim, lowercase عند الحاجة، tokenize, sort, unique.

### 3.2 أنواع القيم المعادة غير ثابتة

بعض `verify()` ترجع `True/False`، وبعض الحالات ترجع strings مثل `Captcha expired` أو `Max attempts reached`. هذا يربك المستهلك ويجبره على مقارنة نصوص بدل التعامل مع exceptions أو result objects. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L88-L125) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L115-L155) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/math.py#L170-L197)

**الاقتراح:** استخدم `CaptchaVerificationResult(success: bool, code: str, message: str)` أو exceptions typed.

### 3.3 الـ logging configuration الحالية غير سليمة تصميميًا

`log_event()` ينادي `setup_logging()` في كل مرة، و`basicConfig` أصلًا لا يُعاد ضبطه كما يتوقع أغلب المطورين. النتيجة أن التدوير اليومي غير مضمون داخل process طويل العمر، كما أن السجلات تحتوي IDs وIP وsession metadata محليًا داخل package directory. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L14-L22)

**الاقتراح:** جهّز logger واحد مرة واحدة، واستعمل `RotatingFileHandler` أو اجعل الـ logging injectable ويمكن إيقافه/تخصيصه.

### 3.4 `__init__.py` غير سليم كواجهة حزمة

`from . import *` داخل `__init__.py` ليس export API نظيف، ويؤدي إلى سلوك غامض وأعلام lint مثل `F403/F401`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/__init__.py#L1-L3)

**الاقتراح:** صدّر فقط الكلاسات العامة بشكل صريح، مثل `from .text import TextCaptcha` وهكذا.

### 3.5 `setup.py` و`pyproject.toml` مكرران وفيهما drift محتمل

فيه ملفان metadata لنفس الحزمة مع معلومات متكررة، ومع متغير `ServerURL` غير مستخدم وdependencies غير ضرورية مثل `requests` الظاهر كمطلوب لكنه غير مستخدم داخل الكود. هذا يزيد فرص التناقض بين النشر والبناء مستقبلًا. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L1-L63) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L1-L45)

**الاقتراح:** انتقل إلى `pyproject.toml` فقط، واحذف `setup.py` إلا لو محتاجه لسبب فعلي واضح.

### 3.6 الـ package artifacts متخمة بملفات لا يجب شحنها

إعداد `package-data = ["**/*"]` تسبب في شحن كل شيء تقريبًا، بما في ذلك `__pycache__`, قاعدة البيانات, الموديل, الصور, الأصوات. النتيجة wheel بحجم كبير وسلوك غير deterministic. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L38-L45) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/setup.py#L26-L29)

**الاقتراح:** حدّد package data بدقة شديدة، واستبعد `__pycache__` و`dbs`، وفكر في تنزيل model/assets عند الطلب بدل شحنها دائمًا.

### 3.7 README والوثائق فيها drift عن الكود الحالي

الـ README ما زالت تشير إلى “Latest Updates (v2.2.x)” بينما version في المشروع `2.3.0`. كذلك أمثلة الاستخدام لا تشرح ضرورة تمرير `ip/session` مع أن الأمن المعروض يعتمد عليهما، ولا تشرح كيف يحصل المستخدم على phrase في `VoiceCaptcha` أو target prompt في `ImageCaptcha`. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/README.md#L123-L130) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/pyproject.toml#L5-L8) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/README.md#L82-L107)

**الاقتراح:** حدّث README بعد إصلاح الـ API، واجعل الأمثلة production-like لا demo-like.

### 3.8 الديون الأسلوبية والهيكلية كبيرة جدًا

الفحص الأسلوبي أظهر عددًا ضخمًا من مخالفات `flake8`: indentation غير قياسي، multiple imports on one line، سطور طويلة جدًا، `bare except`, وتعريفات/تعليقات غير منسقة. ده مش مجرد تجميل؛ غالبًا يكون مؤشر على صعوبة الصيانة وارتفاع احتمال إدخال bugs مستقبلًا. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/math.py#L20-L27) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L1-L6) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/cli.py#L1-L10)

**الاقتراح:** فعّل `ruff` أو `black + isort + flake8` داخل pre-commit وCI.

---

## 4) مشاكل إضافية وظيفية/تصميمية

### 4.1 `TextCaptcha` العربية غير مقنعة كـ feature حقيقية

وضع `lang='ar'` يعيد تشكيل النص عربيًا، لكن النص نفسه مولد من أحرف لاتينية/أرقام كبيرة (`ABCDEFGHJKLMNPQRSTUVWXYZ23456789`). بالتالي “الدعم العربي” هنا شكلي أكثر من كونه دعمًا فعليًا لمحتوى عربي. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L45-L67)

**الاقتراح:** لو عايز دعم عربي حقيقي، ولّد alphabet عربي منفصل وخطوط مناسبة وقواعد normalization خاصة به.

### 4.2 `AudioCaptcha` لا يتحقق من sample rate أو format consistency

الكود يقرأ WAV ثم يبني الخرج على فرضية 44.1kHz ويطبق low-pass ثابت. لو ملفات المصدر تغيرت مستقبلًا أو كانت بخصائص مختلفة، سلوك الصوت سيتدهور بدون حماية واضحة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L9-L18) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/audio.py#L67-L81)

**الاقتراح:** خزّن metadata للأصول الصوتية أو أعد resample صراحة قبل الدمج.

### 4.3 `CodeQL` issue automation فيها احتمال فشل منطقي/تنفيذي

في workflow الـ CodeQL يتم استدعاء API ثم التعامل مع الناتج كأنه يحتوي مفتاح `alerts`، بينما endpoint المعتاد يرجّع array مباشرة، كما أن خطوة إنشاء القضايا تستخدم `$GITHUB_TOKEN` داخل shell بدون تمريره صراحة في هذه الخطوة. النتيجة المتوقعة: step هشة وغير مضمونة. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/codeql.yml#L34-L75)

**الاقتراح:** إمّا احذف الـ auto-issue logic أو نفّذها بصورة أبسط بعد التحقق من schema الحقيقية لرد GitHub API.

---

## 5) ترتيب الأولويات المقترح للإصلاح

### المرحلة 1 — خلال 24 إلى 48 ساعة

1. إصلاح bypass الخاص بـ `ip/session` في كل `verify`.
2. إيقاف شحن `captcha.db` نهائيًا.
3. تعطيل `readme-workflow.yml` ووقف النشر التلقائي المعتمد عليه.
4. إصلاح `VoiceCaptcha.create()` بحيث يحتفظ بالـ prompt الواضح للمستخدم.
5. إصلاح `ImageCaptcha` لفلترة detections حسب الفئة المطلوبة.

### المرحلة 2 — خلال أسبوع

1. إعادة تصميم API لتكون stateless-friendly: `create -> challenge object`, `verify(captcha_id, response, context)`.
2. إزالة cleanup threads من الـ instances.
3. إعادة بناء الاختبارات والـ CI.
4. إخراج storage/logging/config إلى backends قابلة للحقن.

### المرحلة 3 — خلال أسبوعين

1. تقسيم dependencies إلى extras (`image`, `audio`, `voice`).
2. تقليل حجم الحزمة وعدم شحن assets غير الضرورية.
3. تنظيف style بالكامل بـ formatter/linter موحد.
4. تحديث README وكتابة threat model بسيط للمشروع.

---

## 6) التقييم النهائي

**التقييم الحالي:** المشروع واعد، لكن في فرع `devmode` ما زال يحتاج إعادة ضبط معمارية وأمنية قبل اعتباره library موثوقة للإنتاج. أخطر ما فيه ليس ثغرة واحدة فقط، بل مجموعة قرارات تصميمية متراكبة: state داخل الحزمة، DB مشحونة، API غير stateless، CI لا يضمن الجودة، وميزات أمنية موثقة لكن قابلة للتجاوز. [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/utils.py#L5-L18) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/InnoCaptcha/text.py#L132-L146) [Source](https://github.com/InnoSoft-Company/InnoCaptcha/blob/devmode/.github/workflows/python-package.yml#L33-L48)

**حكم مختصر:**
- **Production-ready الآن؟** لا.
- **قابل للإصلاح؟** نعم جدًا.
- **أين تبدأ؟** الأمن الحقيقي أولًا: context binding, storage design, Voice/Image logic, ثم CI والاختبارات.

---

## 7) اقتراح إعادة تصميم مختصرة جدًا

```python
@dataclass
class CaptchaChallenge:
    id: str
    kind: str
    prompt: str | None
    payload: bytes | str | dict
    expires_at: datetime

class CaptchaStore(Protocol):
    def save(self, challenge: CaptchaChallenge, answer_hash: str, context: dict | None): ...
    def load(self, captcha_id: str): ...
    def delete(self, captcha_id: str): ...

class CaptchaVerifier:
    def verify(self, captcha_id: str, response: str | bytes, context: dict | None) -> VerificationResult: ...
```

بهذا الشكل ستفصل التوليد عن التخزين عن التحقق، وتسهّل الاختبار، وتمنع الاعتماد على state داخل object واحد.
