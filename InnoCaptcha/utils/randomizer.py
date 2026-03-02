"""
captcha_lib.utils.randomizer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Cryptographically-secure random generation utilities.

All functions use Python's ``secrets`` module to ensure unpredictability
suitable for security-sensitive CAPTCHA generation.
"""

from __future__ import annotations

import secrets
import string
from typing import Tuple


# ---------------------------------------------------------------------------
# Character sets
# ---------------------------------------------------------------------------

#: Characters used for image CAPTCHA (ambiguous chars removed).
CAPTCHA_CHARS: str = "23456789abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ"

#: Digits only
DIGIT_CHARS: str = string.digits


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def random_float(min_val: float, max_val: float) -> float:
    """Return a cryptographically-secure random float in ``[min_val, max_val]``.

    Args:
        min_val: Lower bound (inclusive).
        max_val: Upper bound (inclusive).

    Returns:
        A random float within the specified range.
    """
    return min_val + (secrets.randbelow(100_000) / 100_000) * (max_val - min_val)


def random_int(min_val: int, max_val: int) -> int:
    """Return a cryptographically-secure random integer in ``[min_val, max_val]``.

    Args:
        min_val: Lower bound (inclusive).
        max_val: Upper bound (inclusive).

    Returns:
        A random integer within the specified range.
    """
    if max_val < min_val:
        raise ValueError(f"max_val ({max_val}) must be >= min_val ({min_val})")
    return secrets.randbelow(max_val - min_val + 1) + min_val


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------


def random_color(
    start: int,
    end: int,
    opacity: int | None = None,
) -> Tuple[int, ...]:
    """Generate a random RGB(A) colour tuple.

    Args:
        start:   Minimum channel value (0–255).
        end:     Maximum channel value (0–255).
        opacity: Optional alpha channel (0–255). If ``None``, returns RGB.

    Returns:
        A ``(r, g, b)`` or ``(r, g, b, a)`` tuple.
    """
    r = random_int(start, end)
    g = random_int(start, end)
    b = random_int(start, end)
    if opacity is None:
        return (r, g, b)
    return (r, g, b, opacity)


def random_text_color() -> Tuple[int, int, int]:
    """Return a random dark colour suitable for CAPTCHA text."""
    return random_color(10, 140)  # type: ignore[return-value]


def random_background_color() -> Tuple[int, int, int]:
    """Return a random light colour suitable for CAPTCHA background."""
    return random_color(220, 255)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Character / string helpers
# ---------------------------------------------------------------------------


def random_chars(length: int, charset: str = CAPTCHA_CHARS) -> str:
    """Return a cryptographically-random string of ``length`` characters.

    Args:
        length:  Number of characters to generate.
        charset: Pool of characters to sample from.

    Returns:
        A random string of the requested length.
    """
    if length < 1:
        raise ValueError("length must be >= 1")
    return "".join(secrets.choice(charset) for _ in range(length))


def random_digits(length: int) -> str:
    """Return a random digit string of the given length.

    Args:
        length: Number of digits.

    Returns:
        A string of random digits.
    """
    return "".join(secrets.choice(DIGIT_CHARS) for _ in range(length))


# ---------------------------------------------------------------------------
# Math problem helpers
# ---------------------------------------------------------------------------


def random_math_problem(
    difficulty: str = "medium",
) -> Tuple[str, int]:
    """Generate a random arithmetic problem and its answer.

    Args:
        difficulty: One of ``"easy"``, ``"medium"``, or ``"hard"``.

    Returns:
        A tuple of ``(problem_string, answer)`` where the problem string is
        suitable for display (e.g. ``"7 + 4"``).
    """
    if difficulty == "easy":
        a = random_int(1, 10)
        b = random_int(1, 10)
        return f"{a} + {b}", a + b

    elif difficulty == "hard":
        op = secrets.choice(["+", "-", "×"])
        if op == "+":
            a = random_int(10, 99)
            b = random_int(10, 99)
            return f"{a} + {b}", a + b
        elif op == "-":
            a = random_int(20, 99)
            b = random_int(1, a)
            return f"{a} - {b}", a - b
        else:  # ×
            a = random_int(2, 12)
            b = random_int(2, 12)
            return f"{a} × {b}", a * b

    else:  # medium
        op = secrets.choice(["+", "-"])
        a = random_int(1, 20)
        b = random_int(1, 20)
        if op == "+":
            return f"{a} + {b}", a + b
        else:
            if a < b:
                a, b = b, a
            return f"{a} - {b}", a - b
