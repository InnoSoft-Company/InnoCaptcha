# InnoCaptcha

[![PyPI Version](https://img.shields.io/pypi/v/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![Python Versions](https://img.shields.io/pypi/pyversions/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![PyPI Status](https://img.shields.io/pypi/status/InnoCaptcha.svg)](https://pypi.org/project/InnoCaptcha/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/InnoSoft-Company/InnoCaptcha/blob/main/LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/InnoSoft-Company/InnoCaptcha)](https://github.com/InnoSoft-Company/InnoCaptcha/commits/main)
[![PyPI Downloads](https://img.shields.io/pypi/dm/InnoCaptcha)](https://pypi.org/project/InnoCaptcha/)
[![Total Downloads](https://static.pepy.tech/personalized-badge/InnoCaptcha?period=total&units=INTERNATIONAL_SYSTEM&left_color=GRAY&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/InnoCaptcha)
[![GitHub stars](https://img.shields.io/github/stars/InnoSoft-Company/InnoCaptcha?style=social)](https://github.com/InnoSoft-Company/InnoCaptcha)

A pluggable Python CAPTCHA library supporting image-based text challenges, arithmetic challenges, token-based security, and multiple storage backends.

**[PyPI](https://pypi.org/project/InnoCaptcha/) · [GitHub](https://github.com/InnoSoft-Company/InnoCaptcha) · [Issues](https://github.com/InnoSoft-Company/InnoCaptcha/issues) · [Discussions](https://github.com/InnoSoft-Company/InnoCaptcha/discussions)**

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Text CAPTCHA](#1-text-captcha)
  - [Math CAPTCHA](#2-math-captcha)
  - [Command-Line Interface](#3-command-line-interface)
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
captcha.create("abc123")
print(captcha.verify("wrong"))  # False
captcha.save(r"captcha.jpg")
```

**Constructor Parameters**

| Parameter    | Type                   | Default           | Description                     |
|--------------|------------------------|-------------------|---------------------------------|
| `width`      | `int` or `None`        | `300`             | Image width in pixels.          |
| `height`     | `int` or `None`        | `80`              | Image height in pixels.         |
| `color`      | `tuple[int, int, int]` | `(0, 0, 0)`       | Foreground (text) color in RGB. |
| `background` | `tuple[int, int, int]` | `(255, 255, 255)` | Background color in RGB.        |

**`create(chars: str)`** — The text string to render in the CAPTCHA image. Required.

**`save()` Parameters**

| Parameter | Type  |     Default     | Description                                                    |
|-----------|-------|-----------------|----------------------------------------------------------------|
| `path`    | `str` | `'captcha.png'` | Full file path or file name to write the image.                |

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

### 3. Command-Line Interface

```bash
# Display the installed version
incaptcha --version

# Upgrade to the latest release on PyPI
incaptcha --upgrade
```

---

## API Reference

### `TextCaptcha`

| Method / Attribute     | Description                                              |
|------------------------|----------------------------------------------------------|
| `create(chars: str)`   | Renders the given string into a distorted CAPTCHA image. |
| `verify(input: str)`   | Returns `True` if `input` matches the generated text.    |
| `save(path)`           | Writes the image to the specified file path.             |

### `MathCaptcha`

| Method / Attribute      | Description                                           |
|-------------------------|-------------------------------------------------------|
| `get_question() -> str` | Returns the challenge string, e.g. `"7 + 3 = ?"`.    |
| `answer: int`           | The correct integer answer to the current challenge.  |
| `verify(input) -> bool` | Returns `True` if `input` equals the answer.          |

---

## Requirements

- Python 3.9 or later
- Pillow >= 10.0.0

---

## License

MIT — [InnoSoft Company](https://github.com/InnoSoft-Company)
