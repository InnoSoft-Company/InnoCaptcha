# InnoCaptcha (نسخة عربية)

تعتبر InnoCaptcha مكتبة Python احترافية وقابلة للتوسع تدعم تحديات الكابتشا المبنية على النصوص، المسائل الحسابية، التحديات الصوتية، وتحديات الصور، مع نظام أمان يعتمد على الرموز (Tokens) وقواعد بيانات SQLite.

---

## جدول المحتويات

- [التثبيت](#التثبيت)
- [البداية السريعة](#البداية-السريعة)
  - [كابتشا النصوص](#1-كابتشا-النصوص)
  - [كابتشا الرياضيات](#2-كابتشا-الرياضيات)
  - [كابتشا الصوت](#3-كابتشا-الصوت)
  - [كابتشا الصور](#4-كابتشا-الصور)
- [مرجع واجهة البرمجة (API)](#مرجع-واجهة-البرمجة-api)
- [المتطلبات](#المتطلبات)
- [الترخيص](#الترخيص)

---

## التثبيت

```bash
pip install InnoCaptcha
```

---

## البداية السريعة

### 1. كابتشا النصوص (Text CAPTCHA)

توليد صورة كابتشا نصية مع إمكانية التحكم في الألوان والأبعاد والخطوط.

```python
from InnoCaptcha.text import TextCaptcha

# استخدام بسيط
captcha = TextCaptcha()
captcha.create("abs")
print(captcha.verify("abs"))    # ناتج: True
captcha.save("captcha.png")
```

### 2. كابتشا الرياضيات (Math CAPTCHA)

توليد مسائل حسابية (جمع، طرح، ضرب).

```python
from InnoCaptcha.math import MathCaptcha

# ناتج نصي
challenge = MathCaptcha()
print(challenge.get_question())  # مثال: "7 + 3 = ?"
print(challenge.verify(10))      # ناتج: True
```

### 3. كابتشا الصوت (Audio CAPTCHA)

توليد ملف صوتي (WAV) ينطق الحروف مع إضافة ضوضاء وتغيير السرعة لزيادة الأمان.

```python
from InnoCaptcha.audio import AudioCaptcha

captcha = AudioCaptcha()
captcha.create("ab3")
captcha.save("captcha.wav")
print(captcha.verify("ab3"))    # ناتج: True
```

---

## التحديثات الجديدة في إصدار 2.2.0

- **الأمان:** تم إلغاء استخدام `eval()` واستبداله بآلية حسابية آمنة.
- **الخصوصية:** تم حذف نظام تتبع التحليلات (Telemetry) لضمان خصوصية المستخدم بالكامل.
- **اللغة العربية:** دعم أولي للغة العربية في التوثيق والرسائل.
- **استقرار النظام:** تحسين إدارة قواعد البيانات وحماية المسارات.

---

## الترخيص

MIT — [InnoSoft Company](https://github.com/InnoSoft-Company)
