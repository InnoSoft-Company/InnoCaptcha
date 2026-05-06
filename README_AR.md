# InnoCaptcha (المكتبة الإبداعية للكابتشا)

[![PyPI Version](https://img.shields.io/pypi/v/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![Python Versions](https://img.shields.io/pypi/pyversions/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/InnoSoft-Company/InnoCaptcha/blob/main/LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/InnoSoft-Company/InnoCaptcha)](https://github.com/InnoSoft-Company/InnoCaptcha/commits/main)

**InnoCaptcha** هي مكتبة بايثون احترافية وشاملة لتوليد تحديات الكابتشا (CAPTCHA). مصممة للتطبيقات الحديثة التي تتطلب أماناً عالياً وتجربة مستخدم مميزة. تدعم المكتبة مجموعة واسعة من التحديات، بدءاً من النصوص التقليدية وصولاً إلى الذكاء الاصطناعي والتعرف على الصوت.

---

## ✨ المميزات الرئيسية

- 📝 **كابتشا النصوص**: توليد صور نصية مشوهة مع حواف ناعمة (Anti-aliasing) وتحكم كامل في الأبعاد والألوان.
- 🔢 **كابتشا الرياضيات**: مسائل حسابية مؤمنة (لا تستخدم `eval()`) مع إمكانية عرضها كنص أو كصورة.
- 🎧 **كابتشا الصوت**: توليد ملفات صوتية (WAV) تنطق الحروف مع إضافة ضوضاء خلفية وتغيير السرعة لزيادة الأمان.
- 🗣️ **كابتشا الصوت المتكلم (STT)**: تحدي جديد يطلب من المستخدم نطق عبارة معينة والتحقق منها برمجياً.
- 🖼️ **كابتشا الصور (YOLOv11)**: تحديات متطورة تعتمد على اكتشاف الأشياء في شبكة 3×3 باستخدام موديل YOLOv11.
- 🔐 **أمان متقدم**:
  - نظام عشوائية قوي يعتمد على مكتبة `secrets`.
  - ربط التحقق بالعنوان (IP) ومعرف الجلسة (Session ID) لمنع الهجمات المكررة.
  - انتهاء صلاحية تلقائي (5 دقائق) وحد أقصى للمحاولات (5 محاولات).
  - تنظيف متزامن لقاعدة البيانات لمنع تسرب الذاكرة.
  - تشفير آمن للبيانات عبر متغير البيئة `INNOCAPTCHA_KEY`.
- 🗄️ **إدارة قواعد البيانات**: نظام مركزي لإدارة البيانات باستخدام SQLite.

---

## 🚀 التثبيت

```bash
pip install InnoCaptcha
```

## 🛠️ البداية السريعة

**مهم**: في بيئة الإنتاج، يرجى تعيين متغير البيئة `INNOCAPTCHA_KEY` بمفتاح `Fernet` آمن لتشفير الإجابات في قاعدة البيانات.

```bash
export INNOCAPTCHA_KEY="your_secure_fernet_key_here"
```

### 1. كابتشا النصوص (Text CAPTCHA)
توليد صورة تحتوي على نص عشوائي مشوه.

```python
from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha(width=300, height=80)
# تمرير عنوان الـ IP ومعرف الجلسة لضمان الأمان
captcha_id = captcha.create("abcd", ip="127.0.0.1", session_id="abc123xyz")
captcha.save("captcha.png")

print(captcha.verify("abcd", ip="127.0.0.1", session_id="abc123xyz")) # يعطي True
```

### 2. كابتشا الرياضيات (Math CAPTCHA)
مسائل حسابية يمكن عرضها كنص أو صورة.

```python
from InnoCaptcha.math import MathCaptcha

# تحدي رياضي بصورة
math_cap = MathCaptcha(output="image")
math_cap.create(ip="127.0.0.1", session_id="abc123xyz")
math_cap.get_question().show() # يعرض تفاصيل المسألة كصورة

# الإجابة تعتمد على المسألة الحسابية التي تم إنشاؤها
print(math_cap.verify("12", ip="127.0.0.1", session_id="abc123xyz"))
```

### 3. كابتشا الصوت (Audio CAPTCHA)
توليد ملف صوتي ينطق الحروف للمستخدم.

```python
from InnoCaptcha.audio import AudioCaptcha

audio = AudioCaptcha()
audio.create("x123", ip="127.0.0.1")
audio.save("output.wav")

print(audio.verify("x123", ip="127.0.0.1"))
```

### 4. كابتشا التحدث (Voice Captcha - جديد!)
تحدي يطلب من المستخدم نطق جملة معينة.

```python
from InnoCaptcha.voice import VoiceCaptcha

vc = VoiceCaptcha(language='ar-EG') # دعم اللغة العربية
captcha_id = vc.create(ip="127.0.0.1") 
print(f"الرجاء قراءة هذه العبارة: {vc.phrase}")

# ... بعد تسجيل المستخدم للصوت ...
audio_bytes = open("user_voice.wav", "rb").read()
is_correct = vc.verify(audio_bytes, ip="127.0.0.1")
```

### 5. كابتشا الصور (Image CAPTCHA)
تحديد المربعات التي تحتوي على كائن معين باستخدام الذكاء الاصطناعي.

```python
from InnoCaptcha.image import ImageCaptcha

img_cap = ImageCaptcha()
img_cap.create(ip="127.0.0.1")
img_cap.save("grid_image.png")
print(f"الكائن المطلوب التعرف عليه: {img_cap.image_class}")

# إدخال أرقام المربعات (مثال: "1,2,5")
print(img_cap.verify("1,2,5", ip="127.0.0.1"))
```

---

## 🆙 أحدث التحديثات (الإصدار 2.3.x)

- **أمان وتصميم برمجي مُحسن**: 
  - حل مشكلات تسرب الذاكرة (Memory Leaks) بإزالة خيوط المعالجة (Threads) في الخلفية واستخدام تنظيف متزامن (Synchronous cleanup).
  - إيقاف هجمات الحقن عبر قواعد البيانات (SQL Injection) باستخدام آلية التحقق (Whitelisting).
  - القضاء على هجمات التوقيت (Timing attacks) عبر استخدام وسائل مقارنة زمنية ثابتة (`secrets.compare_digest`).
  - تطوير نظام التشفير لاستخدام متغير البيئة `INNOCAPTCHA_KEY`، مما يبعد مفتاح التشفير عن قاعدة البيانات نفسها.
  - إعداد تحديثات ذرية (Atomic updates) لعدادات المحاولات لحل مشكلات السباق (Race conditions).
  - تحسين كابتشا الصور (`ImageCaptcha`) عن طريق تخزين وتفعيل نموذج `YOLOv11` بشكل عام (Singleton)، مما سرّع من أوقات التحميل المتكررة بشكل كبير.

---

## 📜 المتطلبات

- بايثون 3.9 أو أحدث.
- المكتبات المطلوبة: `Pillow`, `numpy`, `scipy`, `ultralytics`, `opencv-python`, `pydub`, `SpeechRecognition`.

---

## 📄 الترخيص

MIT © [InnoSoft Company](https://github.com/InnoSoft-Company)
