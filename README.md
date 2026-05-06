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
  - Automatic expiration (5 minutes) and attempt limits (5 attempts).
  - Synchronous cleanup for expired challenges to prevent memory leaks.
  - Secure data encryption via `INNOCAPTCHA_KEY`.
- 🗄️ **Storage**: Centralized SQLite database management.

---

## 🚀 Installation

```bash
pip install InnoCaptcha
```

## 🛠️ Quick Start

**Important**: For production, please set the `INNOCAPTCHA_KEY` environment variable to a secure `Fernet` key to encrypt answers in the database.

```bash
export INNOCAPTCHA_KEY="your_secure_fernet_key_here"
```

### 1. Text CAPTCHA
Generates a distorted image containing a random string.

```python
from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha(width=300, height=80)
# Pass IP and session ID for context binding
captcha_id = captcha.create("abcd", ip="127.0.0.1", session_id="abc123xyz")
captcha.save("captcha.png")

print(captcha.verify("abcd", ip="127.0.0.1", session_id="abc123xyz")) # Returns True
```

### 2. Math CAPTCHA
Generates arithmetic challenges. Can be output as plain text or a rendered image.

```python
from InnoCaptcha.math import MathCaptcha

# Image-based Math Challenge
math_cap = MathCaptcha(output="image")
math_cap.create(ip="127.0.0.1", session_id="abc123xyz")
math_cap.get_question().show() # Returns a PIL Image

# Answer depends on the generated math question
print(math_cap.verify("12", ip="127.0.0.1", session_id="abc123xyz"))
```

### 3. Audio CAPTCHA
Generates a WAV file where a voice reads out characters.

```python
from InnoCaptcha.audio import AudioCaptcha

audio = AudioCaptcha()
audio.create("x123", ip="127.0.0.1")
audio.save("output.wav")

print(audio.verify("x123", ip="127.0.0.1"))
```

### 4. Voice CAPTCHA (New!)
A speech-to-text challenge. The user is given a phrase and must submit a recording of them speaking it.

```python
from InnoCaptcha.voice import VoiceCaptcha

vc = VoiceCaptcha(language='en-US')
captcha_id = vc.create(ip="127.0.0.1") 
print(f"Please read: {vc.phrase}")

# ... User records audio and sends bytes ...
audio_bytes = open("user_speech.wav", "rb").read()
is_correct = vc.verify(audio_bytes, ip="127.0.0.1")
```

### 5. Image CAPTCHA (YOLOv11)
Uses YOLOv11 to detect objects in an image and asks the user to select the grid cells (1-9).

```python
from InnoCaptcha.image import ImageCaptcha

img_cap = ImageCaptcha()
img_cap.create(ip="127.0.0.1")
img_cap.save("grid_image.png")
print(f"Target object to detect: {img_cap.image_class}")

# User inputs cell numbers, e.g., "1,2,5"
print(img_cap.verify("1,2,5", ip="127.0.0.1"))
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

## 🆙 Latest Updates (v2.3.x)

- **New Security & Architecture Audit Fixes**: 
  - Addressed memory leaks by removing background threading loops per instance.
  - Patched an SQL injection via `ALLOWED_TABLES` whitelisting.
  - Eliminated timing attacks across all context verifications using `secrets.compare_digest`.
  - Moved DB Encryption to require an `INNOCAPTCHA_KEY` variable, keeping the encryption key out of the SQLite DB itself.
  - Implemented atomic updates for attempt counters to eliminate race conditions.
  - Optimized `ImageCaptcha` to use a global cached singleton for its `YOLOv11` model, vastly speeding up subsequent initializations.

---

## 📜 Requirements

- Python 3.9+
- Dependencies: `Pillow`, `numpy`, `scipy`, `ultralytics`, `opencv-python`, `pydub`, `SpeechRecognition`, etc.

---

## 📄 License

MIT © [InnoSoft Company](https://github.com/InnoSoft-Company)