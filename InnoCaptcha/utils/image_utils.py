"""
captcha_lib.utils.image_utils
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Low-level image-manipulation helpers for CAPTCHA rendering.

All Pillow-specific logic lives here so that higher-level modules remain
decoupled from the image library.  This module is a direct refactoring of
the original ``image.py`` functions with improved thread safety, type hints,
and configurable distortion parameters.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Sequence, Tuple

from PIL.Image import Image, Transform, Resampling, new as _new_image
from PIL.ImageDraw import Draw
from PIL.ImageFilter import SMOOTH
from PIL.ImageFont import FreeTypeFont, truetype

from ..utils.randomizer import random_float, random_int

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ColorTuple = Tuple[int, ...]          # (r, g, b) or (r, g, b, a)
FontList   = List[FreeTypeFont]

# Look-up table used for alpha masking characters onto the background
_LOOKUP_TABLE: List[int] = [int(i * 1.97) for i in range(256)]

# ---------------------------------------------------------------------------
# Thread-safe font cache
# ---------------------------------------------------------------------------

_font_cache: Dict[Tuple, FontList] = {}
_font_lock:  threading.Lock      = threading.Lock()

# Shared dummy canvas for off-screen text measurement
_dummy_canvas = _new_image("RGBA", (1, 1))
_dummy_draw   = Draw(_dummy_canvas)
_dummy_lock:  threading.Lock = threading.Lock()


def get_truefonts(
    fonts: Sequence[str],
    font_sizes: Sequence[int],
) -> FontList:
    """Load :class:`FreeTypeFont` objects for every ``(font, size)`` pair.

    Results are cached per unique ``(fonts, font_sizes)`` combination using a
    thread-safe dictionary so the expensive disk read happens only once.

    Args:
        fonts:      Paths to ``.ttf`` / ``.otf`` font files.
        font_sizes: Point sizes to load for each font.

    Returns:
        A flat list of :class:`FreeTypeFont` objects.
    """
    cache_key = (tuple(fonts), tuple(font_sizes))
    with _font_lock:
        if cache_key in _font_cache:
            return _font_cache[cache_key]
        font_list: FontList = [
            truetype(path, size)
            for path in fonts
            for size in font_sizes
        ]
        _font_cache[cache_key] = font_list
        return font_list


def clear_font_cache() -> None:
    """Evict all entries from the font cache.

    Useful after changing font configuration at runtime.
    """
    with _font_lock:
        _font_cache.clear()


# ---------------------------------------------------------------------------
# Noise generators
# ---------------------------------------------------------------------------


def create_noise_dots(
    image: Image,
    color: ColorTuple,
    width: int = 3,
    number: int = 30,
) -> Image:
    """Draw *number* randomly-placed dot-noise marks onto *image*.

    Args:
        image:  The PIL image to draw onto (mutated in place).
        color:  RGB colour for the dots.
        width:  Stroke width in pixels.
        number: Number of dots to draw.

    Returns:
        The same *image* object (mutated).
    """
    draw = Draw(image)
    w, h = image.size
    for _ in range(number):
        x = random_int(0, w)
        y = random_int(0, h)
        draw.line(((x, y), (x - 1, y - 1)), fill=color, width=width)
    return image


def create_noise_curve(
    image: Image,
    color: ColorTuple,
) -> Image:
    """Draw a single random arc onto *image* to add visual noise.

    Args:
        image: The PIL image to draw onto (mutated in place).
        color: RGB colour for the arc.

    Returns:
        The same *image* object (mutated).
    """
    w, h = image.size
    x1 = random_int(0, w // 5)
    x2 = random_int(w - w // 5, w)
    y1 = random_int(h // 5, h - h // 5)
    y2 = random_int(y1, h - h // 5)
    end   = random_int(160, 200)
    start = random_int(0, 20)
    Draw(image).arc([x1, y1, x2, y2], start, end, fill=color)
    return image


# ---------------------------------------------------------------------------
# Character rendering
# ---------------------------------------------------------------------------


def draw_character(
    char: str,
    color: ColorTuple,
    fonts: Sequence[str],
    font_sizes: Sequence[int],
    character_rotate: Tuple[int, int] = (-30, 30),
    character_warp_dx: Tuple[float, float] = (0.1, 0.3),
    character_warp_dy: Tuple[float, float] = (0.2, 0.3),
    character_offset_dx: Tuple[int, int] = (0, 4),
    character_offset_dy: Tuple[int, int] = (0, 6),
) -> Image:
    """Render a single character with random rotation and perspective warp.

    Args:
        char:                Single character string to draw.
        color:               RGB fill colour.
        fonts:               Font file paths.
        font_sizes:          Point sizes to choose from.
        character_rotate:    ``(min_deg, max_deg)`` rotation range.
        character_warp_dx:   X-axis quadrilateral warp factor range.
        character_warp_dy:   Y-axis quadrilateral warp factor range.
        character_offset_dx: Random horizontal padding range (pixels).
        character_offset_dy: Random vertical padding range (pixels).

    Returns:
        A transparent RGBA :class:`PIL.Image` containing the character.
    """
    import secrets as _s

    truefonts = get_truefonts(fonts, font_sizes)
    font: FreeTypeFont = _s.choice(truefonts)

    # Measure character bounds on the shared dummy canvas
    with _dummy_lock:
        _, _, w, h = _dummy_draw.multiline_textbbox((1, 1), char, font=font)

    # Random padding offsets
    dx1 = random_int(*character_offset_dx)
    dy1 = random_int(*character_offset_dy)

    # Render onto a transparent RGBA canvas
    char_img: Image = _new_image("RGBA", (int(w) + dx1, int(h) + dy1))
    Draw(char_img).text((dx1, dy1), char, font=font, fill=color)

    # Tight-crop to rendered pixels
    bbox = char_img.getbbox()
    if bbox:
        char_img = char_img.crop(bbox)

    # --- Rotation ---
    angle = random_float(*character_rotate)
    char_img = char_img.rotate(angle, Resampling.BILINEAR, expand=True)

    # --- Perspective warp (QUAD transform) ---
    dxw = w * random_float(*character_warp_dx)
    dyw = h * random_float(*character_warp_dy)

    x1 = int(random_float(-dxw, dxw))
    y1 = int(random_float(-dyw, dyw))
    x2 = int(random_float(-dxw, dxw))
    y2 = int(random_float(-dyw, dyw))

    w2 = int(w) + abs(x1) + abs(x2)
    h2 = int(h) + abs(y1) + abs(y2)

    data = (
        x1, y1,
        -x1, h2 - y2,
        w2 + x2, h2 + y2,
        w2 - x2, -y1,
    )

    char_img = char_img.resize((w2, h2))
    char_img = char_img.transform((int(w), int(h)), Transform.QUAD, data)
    return char_img


# ---------------------------------------------------------------------------
# Full image composition
# ---------------------------------------------------------------------------


def create_captcha_image(
    chars: str,
    text_color: ColorTuple,
    background: ColorTuple,
    fonts: Sequence[str],
    font_sizes: Sequence[int],
    width: int = 160,
    height: int = 60,
    noise_dots: int = 30,
    noise_curves: int = 1,
    word_space_probability: float = 0.5,
    word_offset_dx: float = 0.25,
    character_rotate: Tuple[int, int] = (-30, 30),
    character_warp_dx: Tuple[float, float] = (0.1, 0.3),
    character_warp_dy: Tuple[float, float] = (0.2, 0.3),
) -> Image:
    """Compose the complete CAPTCHA image from individual character glyphs.

    Args:
        chars:                  The text string to render.
        text_color:             RGB colour for glyph rendering.
        background:             RGB background colour.
        fonts:                  Font file paths.
        font_sizes:             Point sizes to choose from.
        width:                  Canvas width in pixels.
        height:                 Canvas height in pixels.
        noise_dots:             Number of dot-noise marks.
        noise_curves:           Number of arc-noise marks.
        word_space_probability: Probability of injecting a space glyph between characters.
        word_offset_dx:         Horizontal scatter factor for character placement.
        character_rotate:       Rotation range.
        character_warp_dx:      X-warp factor range.
        character_warp_dy:      Y-warp factor range.

    Returns:
        A composed RGB :class:`PIL.Image`.
    """
    import secrets as _s

    original_width = width

    # Build background canvas
    image: Image = _new_image("RGB", (width, height), background)

    # Render all glyphs (with optional space injections)
    glyph_images: List[Image] = []
    for c in chars:
        if random_float(0.0, 1.0) > word_space_probability:
            glyph_images.append(
                draw_character(
                    " ", text_color, fonts, font_sizes,
                    character_rotate=character_rotate,
                    character_warp_dx=character_warp_dx,
                    character_warp_dy=character_warp_dy,
                )
            )
        glyph_images.append(
            draw_character(
                c, text_color, fonts, font_sizes,
                character_rotate=character_rotate,
                character_warp_dx=character_warp_dx,
                character_warp_dy=character_warp_dy,
            )
        )

    # Expand canvas if text overflows
    text_width = sum(g.size[0] for g in glyph_images)
    if text_width > width:
        width = text_width
        image = image.resize((width, height))

    # Composite glyphs with random scatter
    avg    = max(text_width // max(len(chars), 1), 1)
    rand   = int(word_offset_dx * avg)
    offset = int(avg * 0.1)

    for glyph in glyph_images:
        gw, gh = glyph.size
        mask = glyph.convert("L").point(_LOOKUP_TABLE)
        image.paste(glyph, (offset, (height - gh) // 2), mask)
        offset += gw + (-_s.randbelow(rand + 1))

    # Shrink back to original width
    if width > original_width:
        image = image.resize((original_width, height))

    # Apply noise layers
    noise_color = text_color
    for _ in range(noise_curves):
        image = create_noise_curve(image, noise_color)
    if noise_dots > 0:
        image = create_noise_dots(image, noise_color, number=noise_dots)

    return image
