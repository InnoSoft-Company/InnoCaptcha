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
  - انتهاء صلاحية تلقائي (5 دقائق) وحد أقصى للمحاولات.
  - تنظيف تلقائي لقاعدة البيانات في الخلفية.
- 🗄️ **إدارة قواعد البيانات**: نظام مركزي لإدارة البيانات باستخدام SQLite.

---

## 🚀 التثبيت

```bash
pip install InnoCaptcha
```

## 🛠️ البداية السريعة

### 1. كابتشا النصوص (Text CAPTCHA)
توليد صورة تحتوي على نص عشوائي مشوه.

```python
from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha(width=300, height=80)
captcha.create("abcd")
captcha.save("captcha.png")

print(captcha.verify("abcd")) # يعطي True
```

### 2. كابتشا الرياضيات (Math CAPTCHA)
مسائل حسابية يمكن عرضها كنص أو صورة.

```python
from InnoCaptcha.math import MathCaptcha

# تحدي رياضي بصورة
math = MathCaptcha(output="image")
math.create()
math.get_question().show() # يعرض تفاصيل المسألة كصورة

print(math.verify("10"))
```

### 3. كابتشا الصوت (Audio CAPTCHA)
توليد ملف صوتي ينطق الحروف للمستخدم.

```python
from InnoCaptcha.audio import AudioCaptcha

audio = AudioCaptcha()
audio.create("x123")
audio.save("output.wav")

print(audio.verify("x123"))
```

### 4. كابتشا التحدث (Voice Captcha - جديد!)
تحدي يطلب من المستخدم نطق جملة معينة.

```python
from InnoCaptcha.voice import VoiceCaptcha

vc = VoiceCaptcha(language='ar-EG') # دعم اللغة العربية
id = vc.create() # يولد جملة عشوائية
# ... بعد تسجيل المستخدم للصوت ...
audio_bytes = open("user_voice.wav", "rb").read()
is_correct = vc.verify(audio_bytes)
```

### 5. كابتشا الصور (Image CAPTCHA)
تحديد المربعات التي تحتوي على كائن معين باستخدام الذكاء الاصطناعي.

```python
from InnoCaptcha.image import ImageCaptcha

img_cap = ImageCaptcha()
img_cap.create()
img_cap.save("grid_image.png")

# إدخال أرقام المربعات (مثال: "1,2,5")
print(img_cap.verify("1,2,5"))
```

---

## 🆙 أحدث التحديثات (الإصدار 2.2.x)

- **وحدة جديدة**: إضافة `VoiceCaptcha` لتحديات التعرف على الكلام.
- **الأمان**:
  - تفعيل خاصية **IP and Session binding** لضمان أن من أنشأ الكابتشا هو من يقوم بحلها.
  - توحيد مسار قواعد البيانات في `InnoCaptcha/data/dbs/`.
- **الأداء**: تحسين خيوط المعالجة (threads) الخاصة بتنظيف البيانات القديمة.
- **البرمجة**: تنسيق الكود بالكامل واستخدام معايير احترافية (2 spaces indentation).

---

## 📜 المتطلبات

- بايثون 3.9 أو أحدث.
- المكتبات المطلوبة: `Pillow`, `numpy`, `scipy`, `ultralytics`, `opencv-python`, `pydub`, `SpeechRecognition`.

---

## 📄 الترخيص

MIT © [InnoSoft Company](https://github.com/InnoSoft-Company)
