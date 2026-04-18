# InnoCaptcha

[![PyPI Version](https://img.shields.io/pypi/v/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![Python Versions](https://img.shields.io/pypi/pyversions/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![PyPI Status](https://img.shields.io/pypi/status/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/InnoSoft-Company/InnoCaptcha/blob/main/LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/InnoSoft-Company/InnoCaptcha)](https://github.com/InnoSoft-Company/InnoCaptcha/commits/main)
[![PyPI Downloads](https://img.shields.io/pypi/dm/InnoCaptcha)](https://pypi.org/project/InnoCaptcha/)
[![Total Downloads](https://static.pepy.tech/personalized-badge/InnoCaptcha?period=total&units=INTERNATIONAL_SYSTEM&left_color=GRAY&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/InnoCaptcha)
[![GitHub stars](https://img.shields.io/github/stars/InnoSoft-Company/InnoCaptcha?style=social)](https://github.com/InnoSoft-Company/InnoCaptcha)
![Visitors Badge API](https://visitor-badge.laobi.icu/badge?page_id=InnoSoft-Company.InnoCaptcha&style=flat)
![Visitors - InnoCaptcha API](https://innocaptcha.midoghanam.site/api/analytics/ReposVisitorsCountShield/)

**InnoCaptcha** is a professional, pluggable Python CAPTCHA library designed for modern web applications. It supports multiple challenge types, from traditional text and math to advanced audio, image-based grid challenges (using YOLOv11), and voice recognition challenges.

---

## 🌟 Key Features

- 📝 **Text CAPTCHA**: Highly configurable image-based text challenges with anti-aliasing and distortion.
- 🔢 **Math CAPTCHA**: Secure arithmetic problems (no `eval()`) with optional image rendering.
- 🎧 **Audio CAPTCHA**: Spoken character sequences with noise injection and variable speed.
- 🗣️ **Voice CAPTCHA (STT)**: Speech-to-text challenges where users must speak a random phrase.
- 🖼️ **Image CAPTCHA (YOLOv11)**: Advanced 3×3 grid challenges using Object Detection.
- 🔐 **Security First**: 
  - Token-based challenge identification.
  - IP and Session binding for verification safety.
  - Automatic expiration (5 minutes) and attempt limits (5-6 attempts).
  - Background cleanup for expired challenges.
- 🗄️ **Storage**: Centralized SQLite database management.

---

## 🚀 Installation

```bash
pip install InnoCaptcha
```

## 🛠️ Quick Start

### 1. Text CAPTCHA
Generates a distorted image containing a random string.

```python
from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha(width=300, height=80)
captcha.create("abcd")
captcha.save("captcha.png")

print(captcha.verify("abcd")) # Returns True
```

### 2. Math CAPTCHA
Generates arithmetic challenges. Can be output as plain text or a rendered image.

```python
from InnoCaptcha.math import MathCaptcha

# Image-based Math Challenge
math = MathCaptcha(output="image")
math.create()
math.get_question().show() # Returns a PIL Image

print(math.verify("Answer"))
```

### 3. Audio CAPTCHA
Generates a WAV file where a voice reads out characters.

```python
from InnoCaptcha.audio import AudioCaptcha

audio = AudioCaptcha()
audio.create("x123")
audio.save("output.wav")

print(audio.verify("x123"))
```

### 4. Voice CAPTCHA (New!)
A speech-to-text challenge. The user is given a phrase and must submit a recording of them speaking it.

```python
from InnoCaptcha.voice import VoiceCaptcha

vc = VoiceCaptcha(language='en-US')
id = vc.create() # Generates a random phrase
# ... User records audio and sends bytes ...
audio_bytes = open("user_speech.wav", "rb").read()
is_correct = vc.verify(audio_bytes)
```

### 5. Image CAPTCHA (YOLOv11)
Uses YOLOv11 to detect objects in an image and asks the user to select the grid cells (1-9).

```python
from InnoCaptcha.image import ImageCaptcha

img_cap = ImageCaptcha()
img_cap.create()
img_cap.save("grid_image.png")

# User inputs cell numbers, e.g., "1,2,5"
print(img_cap.verify("1,2,5"))
```

---

## 💎 API Reference

| Component | Description |
|-----------|-------------|
| `TextCaptcha` | Classic image-text challenges. Supports custom colors/scaling. |
| `MathCaptcha` | Arithmetic challenges (+, -, *). Supports `text` or `image` output. |
| `AudioCaptcha` | Generates character-based audio files for auditory verification. |
| `VoiceCaptcha` | Speech-to-text verification using `speech_recognition`. |
| `ImageCaptcha` | AI-powered grid identification using YOLOv11. |

---

## 🆙 Latest Updates (v2.2.x)

- **New Module**: Added `VoiceCaptcha` for speech-to-text challenges.
- **Security**: 
  - Implemented **IP and Session binding** to prevent cross-session replay attacks.
  - Centralized database management in `InnoCaptcha/data/dbs/`.
- **Performance**: Optimized background cleanup threads.
- **Improvements**: Standardized indentation (2 spaces) and removed insecure functions.

---

## 📜 Requirements

- Python 3.9+
- Dependencies: `Pillow`, `numpy`, `scipy`, `ultralytics`, `opencv-python`, `pydub`, `SpeechRecognition`, etc.

---

## 📄 License

MIT © [InnoSoft Company](https://github.com/InnoSoft-Company)