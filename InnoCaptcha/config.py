"""
captcha_lib.config
~~~~~~~~~~~~~~~~~~
Centralised configuration management for the CAPTCHA library.

Usage::

    from captcha_lib.config import CaptchaConfig, DifficultyLevel, get_default_config

    cfg = CaptchaConfig(difficulty=DifficultyLevel.HARD, length=8)
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class DifficultyLevel(str, Enum):
    """Captcha difficulty presets.

    Attributes:
        EASY:   Simple short captchas with low noise.
        MEDIUM: Moderate length captchas with noise (default).
        HARD:   Long captchas with heavy distortion and noise.
    """

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class OutputFormat(str, Enum):
    """Supported image output formats."""

    PNG = "PNG"
    JPEG = "JPEG"
    WEBP = "WEBP"


# ---------------------------------------------------------------------------
# Data directory helpers
# ---------------------------------------------------------------------------

_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_DEFAULT_FONT = os.path.join(_DATA_DIR, "DroidSansMono.ttf")


# ---------------------------------------------------------------------------
# Difficulty presets
# ---------------------------------------------------------------------------

_DIFFICULTY_PRESETS: dict[DifficultyLevel, dict] = {
    DifficultyLevel.EASY: {
        "length": 4,
        "noise_dots": 15,
        "noise_curves": 0,
        "font_sizes": (38, 44, 48),
        "character_rotate": (-15, 15),
        "character_warp_dx": (0.05, 0.1),
        "character_warp_dy": (0.1, 0.15),
    },
    DifficultyLevel.MEDIUM: {
        "length": 6,
        "noise_dots": 30,
        "noise_curves": 1,
        "font_sizes": (42, 50, 56),
        "character_rotate": (-30, 30),
        "character_warp_dx": (0.1, 0.3),
        "character_warp_dy": (0.2, 0.3),
    },
    DifficultyLevel.HARD: {
        "length": 8,
        "noise_dots": 50,
        "noise_curves": 2,
        "font_sizes": (44, 52, 58),
        "character_rotate": (-45, 45),
        "character_warp_dx": (0.2, 0.4),
        "character_warp_dy": (0.3, 0.4),
    },
}


# ---------------------------------------------------------------------------
# CaptchaConfig
# ---------------------------------------------------------------------------


@dataclass
class CaptchaConfig:
    """Immutable configuration object for captcha generation and validation.

    Args:
        captcha_type:       Plugin name to use (``"image"``, ``"math"``, …).
        difficulty:         Difficulty level preset.
        length:             Number of characters (overrides difficulty preset).
        width:              Image width in pixels.
        height:             Image height in pixels.
        fonts:              List of font file paths.
        font_sizes:         Tuple of font sizes to randomly pick from.
        expiry_seconds:     Token validity window in seconds.
        max_attempts:       Max verification attempts before locking.
        case_sensitive:     Whether answer matching is case-sensitive.
        output_format:      Default image output format.
        noise_dots:         Number of noise dots (overrides difficulty preset).
        noise_curves:       Number of noise arcs (overrides difficulty preset).
        character_rotate:   Min/max rotation degrees.
        character_warp_dx:  X-axis warp factor range.
        character_warp_dy:  Y-axis warp factor range.
        secret_key:         HMAC secret key (auto-generated if omitted).
    """

    captcha_type: str = "image"
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    length: Optional[int] = None
    width: int = 160
    height: int = 60
    fonts: List[str] = field(default_factory=lambda: [_DEFAULT_FONT])
    font_sizes: Optional[Tuple[int, ...]] = None
    expiry_seconds: int = 300
    max_attempts: int = 3
    case_sensitive: bool = False
    output_format: OutputFormat = OutputFormat.PNG
    noise_dots: Optional[int] = None
    noise_curves: Optional[int] = None
    character_rotate: Optional[Tuple[int, int]] = None
    character_warp_dx: Optional[Tuple[float, float]] = None
    character_warp_dy: Optional[Tuple[float, float]] = None
    secret_key: Optional[str] = None

    def __post_init__(self) -> None:
        self._apply_difficulty_preset()

    def _apply_difficulty_preset(self) -> None:
        """Fill in None fields from the difficulty preset."""
        preset = _DIFFICULTY_PRESETS[self.difficulty]
        if self.length is None:
            self.length = preset["length"]
        if self.font_sizes is None:
            self.font_sizes = preset["font_sizes"]
        if self.noise_dots is None:
            self.noise_dots = preset["noise_dots"]
        if self.noise_curves is None:
            self.noise_curves = preset["noise_curves"]
        if self.character_rotate is None:
            self.character_rotate = preset["character_rotate"]
        if self.character_warp_dx is None:
            self.character_warp_dx = preset["character_warp_dx"]
        if self.character_warp_dy is None:
            self.character_warp_dy = preset["character_warp_dy"]

    @classmethod
    def easy(cls, **kwargs) -> "CaptchaConfig":
        """Convenience constructor for easy difficulty."""
        return cls(difficulty=DifficultyLevel.EASY, **kwargs)

    @classmethod
    def medium(cls, **kwargs) -> "CaptchaConfig":
        """Convenience constructor for medium difficulty."""
        return cls(difficulty=DifficultyLevel.MEDIUM, **kwargs)

    @classmethod
    def hard(cls, **kwargs) -> "CaptchaConfig":
        """Convenience constructor for hard difficulty."""
        return cls(difficulty=DifficultyLevel.HARD, **kwargs)

    def replace(self, **kwargs) -> "CaptchaConfig":
        """Return a new config with specific fields overridden."""
        import dataclasses
        return dataclasses.replace(self, **kwargs)


# ---------------------------------------------------------------------------
# Global default config (singleton-style, thread-safe)
# ---------------------------------------------------------------------------

_default_config: CaptchaConfig = CaptchaConfig()
_config_lock: threading.Lock = threading.Lock()


def get_default_config() -> CaptchaConfig:
    """Return the current global default :class:`CaptchaConfig`.

    Returns:
        The active default configuration instance.
    """
    with _config_lock:
        return _default_config


def set_default_config(config: CaptchaConfig) -> None:
    """Replace the global default configuration.

    Args:
        config: New :class:`CaptchaConfig` to use as the default.
    """
    global _default_config
    if not isinstance(config, CaptchaConfig):
        raise TypeError(f"Expected CaptchaConfig, got {type(config).__name__}")
    with _config_lock:
        _default_config = config
