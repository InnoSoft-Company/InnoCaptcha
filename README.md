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

A pluggable Python CAPTCHA library supporting image-based text challenges, arithmetic challenges, audio challenges, token-based security, and multiple storage backends.

**[PyPI](https://pypi.org/project/InnoCaptcha/) · [GitHub](https://github.com/InnoSoft-Company/InnoCaptcha) · [Issues](https://github.com/InnoSoft-Company/InnoCaptcha/issues) · [Discussions](https://github.com/InnoSoft-Company/InnoCaptcha/discussions)**

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Text CAPTCHA](#1-text-captcha)
  - [Math CAPTCHA](#2-math-captcha)
  - [Audio CAPTCHA](#3-audio-captcha)
  - [Image CAPTCHA](#4-image-captcha)
  - [Command-Line Interface](#5-command-line-interface)
- [API Reference](#api-reference)
- [Requirements](#requirements)
- [License](#license)

---

## Installation

```bash
pip install InnoCaptcha
```

---

## Quick Start

### 1. Text CAPTCHA

Generates an image-based CAPTCHA with configurable text, colors, and dimensions. All images include random distortions and anti-aliasing.

```python
from InnoCaptcha.text import TextCaptcha

# Basic usage
captcha = TextCaptcha()
captcha.create("abs")
print(captcha.verify("abs"))    # True
captcha.save(r"captcha.png")

# Custom dimensions and colors
captcha = TextCaptcha(
    width=350,
    height=100,
    color=(255, 137, 6),
    background=(15, 14, 23)
)
captcha.create()
print(captcha.verify('Answer'))
captcha.save(r"captcha.jpg")
```

**Constructor Parameters**

| Parameter    | Type                   | Default        | Description                     |
|--------------|------------------------|----------------|---------------------------------|
| `width`      | `int` or `None`        | `300`          | Image width in pixels.          |
| `height`     | `int` or `None`        | `80`           | Image height in pixels.         |
| `color`      | `tuple[int, int, int]` | `Random color` | Foreground (text) color in RGB. |
| `background` | `tuple[int, int, int]` | `Random color` | Background color in RGB.        |

**`create(chars: str)`** — The text string to render in the CAPTCHA image. Optional.

**`save()` Parameters**

| Parameter | Type  | Default         | Description                                     |
|-----------|-------|-----------------|-------------------------------------------------|
| `path`    | `str` | `'captcha.png'` | Full file path or file name to write the image. |

> **Notes:**
> - Uses `secrets` for cryptographically strong randomness.
> - Rendering can be tuned via module-level constants such as `CHARACTER_OFFSET_DX` and `WORD_SPACE_PROBABILITY`.

---

### 2. Math CAPTCHA

Generates arithmetic challenges (addition, subtraction, multiplication, division). All results are integers — the problem regenerates automatically if division would produce a fraction.

```python
from InnoCaptcha.math import MathCaptcha

challenge = MathCaptcha()
print(challenge.get_question())  # e.g., "7 + 3 = ?"
print(challenge.answer)          # e.g., 10

print(challenge.verify(10))      # True
print(challenge.verify("10"))    # True — string input accepted
```

---

### 3. Audio CAPTCHA

Generates a spoken character sequence as a WAV file. Each character is spliced from pre-recorded audio samples stored in the `data/` directory, with per-character noise injection, randomized playback speed, and a low-pass filter applied to the combined output. Challenge state is persisted in SQLite with a 5-minute expiry and a 5-attempt limit.

```python
from InnoCaptcha.audio import AudioCaptcha

# Basic usage
captcha = AudioCaptcha()
captcha.create("ab3")
captcha.save("captcha.wav")

print(captcha.verify("ab3"))    # True
print(captcha.verify("wrong"))  # False
```

**`create(chars: str)`** — Accepts up to 6 characters. Each character must have a corresponding `<char>.wav` file in the `data/` directory. Raises `FileNotFoundError` if any file is missing.

**`save()` Parameters**

| Parameter | Type  | Default | Description                                  |
|-----------|-------|---------|----------------------------------------------|
| `path`    | `str` | —       | Full file path to write the output WAV file. |

**`verify(user_input: str) -> bool or str`**

| Return value          | Condition                                                |
|-----------------------|----------------------------------------------------------|
| `True`                | Input matches the stored answer (case-insensitive).      |
| `False`               | Input does not match; attempt counter incremented.       |
| `str` (error message) | Captcha expired or maximum attempts (5) reached.         |

> **Notes:**
> - Uses `secrets` for randomness in noise generation and speed variation.
> - A background thread runs on instantiation to purge expired records from the database.
> - Output is a 44100 Hz, 16-bit, mono WAV file.

---

### 4. Image CAPTCHA

Presents a 3×3 grid overlay on a randomly selected image. The user identifies which grid cells contain the target object. Detection is performed using YOLOv11n — cells are marked correct if any detected bounding box overlaps them. Challenge state is persisted in SQLite with a 5-minute expiry and a 6-attempt limit.

```python
from InnoCaptcha.image import ImageCaptcha

captcha = ImageCaptcha()
captcha.create()
print(captcha.verify())  # True, False, or str on expiry/lockout
```

**`create()`** — Loads a random image from the dataset, runs YOLO inference to locate objects, and draws a 3×3 blue grid over the result. Must be called before `verify()`.

**`verify() -> bool or str`** — Displays the gridded image and prompts the user to enter the cell numbers (1–9, comma-separated) containing the detected object. Returns `True` only if the submitted cells exactly match all cells that overlap a detected bounding box.

**`verify(user_input: str) -> bool or str`**

| Return value          | Condition                                                |
|-----------------------|----------------------------------------------------------|
| `True`                | Submitted cells exactly match all detected object cells. |
| `False`               | Input does not match; attempt counter incremented.       |
| `str` (error message) | Captcha expired or maximum attempts (6) reached.         |

> **Notes:**
> - Grid numbering is row-major: 1–3 top row, 4–6 middle row, 7–9 bottom row.
> - Image dataset must be structured as `data/images/<class>/<filename>`.
> - Uses `secrets` for random image selection.
> - A background thread runs on instantiation to purge expired records from the database.

---

### 5. Command-Line Interface

```bash
# Display the installed version
InnoCaptcha --version

# Upgrade to the latest release on PyPI
InnoCaptcha --upgrade
```

---

## API Reference

### `TextCaptcha`

| Method / Attribute   | Description                                              |
|----------------------|----------------------------------------------------------|
| `create(chars: str)` | Renders the given string into a distorted CAPTCHA image. |
| `verify(input: str)` | Returns `True` if `input` matches the generated text.    |
| `save(path)`         | Writes the image to the specified file path.             |

### `MathCaptcha`

| Method / Attribute      | Description                                          |
|-------------------------|------------------------------------------------------|
| `get_question() -> str` | Returns the challenge string, e.g. `"7 + 3 = ?"`.   |
| `answer: int`           | The correct integer answer to the current challenge. |
| `verify(input) -> bool` | Returns `True` if `input` equals the answer.         |

### `AudioCaptcha`

| Method / Attribute   | Description                                                                       |
|----------------------|-----------------------------------------------------------------------------------|
| `create(chars: str)` | Builds the audio challenge from up to 6 characters using per-character WAV files. |
| `verify(input: str)` | Returns `True` on match, `False` on mismatch, or a `str` on expiry/lockout.      |
| `save(path: str)`    | Writes the generated audio to a 44100 Hz 16-bit mono WAV file.                   |
| `id: str`            | The hex token identifying this challenge in the database.                         |
| `audio: np.ndarray`  | Raw float32 audio samples; `None` until `create()` is called.                    |

### `ImageCaptcha`

| Method / Attribute       | Description                                                              |
|--------------------------|--------------------------------------------------------------------------|
| `create()`               | Runs YOLO detection on a random dataset image and overlays a 3×3 grid.  |
| `verify() -> bool or str`| Displays the image, accepts grid input, returns `True` on exact match.  |
| `id: str`                | The hex token identifying this challenge in the database.                |
| `image_class: str`       | The randomly selected object class for the current challenge.            |
| `annotation_coordinates` | List of `(x1, y1, x2, y2)` bounding boxes from YOLO inference.          |

---

## Requirements

- Python 3.9 or later
- Pillow >= 10.0.0
- numpy
- scipy
- ultralytics
- opencv-python

---

## License

MIT — [InnoSoft Company](https://github.com/InnoSoft-Company)