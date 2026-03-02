"""
captcha_lib.core.generator
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Orchestration layer for image CAPTCHA generation.

:class:`ImageCaptchaGenerator` wires together the utility modules
(randomizer, image_utils) and the captcha config to produce a finished
PIL Image.  It also supports asynchronous generation via
:meth:`generate_async` using :func:`asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Tuple

from ..config import CaptchaConfig
from ..utils import image_utils as _img
from ..utils.randomizer import random_background_color, random_text_color

logger = logging.getLogger(__name__)


class ImageCaptchaGenerator:
    """Orchestrates the full image CAPTCHA rendering pipeline.

    The generator is stateless — each call to :meth:`generate` produces an
    independent image.  It caches nothing beyond its config reference.

    Args:
        config: A :class:`~captcha_lib.config.CaptchaConfig` instance
                controlling all rendering parameters.
    """

    def __init__(self, config: CaptchaConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate(
        self,
        chars: str,
        text_color: Optional[Tuple[int, int, int]] = None,
        background: Optional[Tuple[int, int, int]] = None,
    ):
        """Render a CAPTCHA image for *chars*.

        Args:
            chars:       The text to embed in the image.
            text_color:  RGB colour for the glyphs.  Auto-selected if ``None``.
            background:  RGB background colour.  Auto-selected if ``None``.

        Returns:
            A :class:`PIL.Image.Image` (RGB mode).
        """
        cfg = self._config

        tc = text_color or random_text_color()
        bg = background or random_background_color()

        logger.debug(
            "Generating image captcha: chars=%r width=%d height=%d noise_dots=%d",
            chars, cfg.width, cfg.height, cfg.noise_dots,
        )

        image = _img.create_captcha_image(
            chars=chars,
            text_color=tc,
            background=bg,
            fonts=cfg.fonts,
            font_sizes=cfg.font_sizes,
            width=cfg.width,
            height=cfg.height,
            noise_dots=cfg.noise_dots,
            noise_curves=cfg.noise_curves,
            character_rotate=cfg.character_rotate,
            character_warp_dx=cfg.character_warp_dx,
            character_warp_dy=cfg.character_warp_dy,
        )

        return image

    async def generate_async(
        self,
        chars: str,
        text_color: Optional[Tuple[int, int, int]] = None,
        background: Optional[Tuple[int, int, int]] = None,
    ):
        """Async wrapper around :meth:`generate` using :func:`asyncio.to_thread`.

        Runs the CPU-bound image generation in a thread pool so it does not
        block the event loop.

        Args:
            chars:       The text to embed in the image.
            text_color:  RGB glyph colour (auto-selected if ``None``).
            background:  RGB background colour (auto-selected if ``None``).

        Returns:
            A :class:`PIL.Image.Image` (RGB mode).
        """
        return await asyncio.to_thread(self.generate, chars, text_color, background)
