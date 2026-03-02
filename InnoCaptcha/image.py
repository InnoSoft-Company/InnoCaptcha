from PIL.Image import new as createImage, Image, Transform, Resampling
from PIL.ImageFont import FreeTypeFont, truetype
from PIL.ImageDraw import Draw, ImageDraw
from PIL.ImageFilter import SMOOTH
from io import BytesIO
import typing as t
import secrets, os

# Type aliases
ColorTuple = t.Union[t.Tuple[int, int, int], t.Tuple[int, int, int, int]]

# Constants
DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
DEFAULT_FONTS = [os.path.join(DATA_DIR, 'DroidSansMono.ttf')]

# Configurable parameters
LOOKUP_TABLE = [int(i * 1.97) for i in range(256)]
CHARACTER_OFFSET_DX = (0, 4)
CHARACTER_OFFSET_DY = (0, 6)
CHARACTER_ROTATE = (-30, 30)
CHARACTER_WARP_DX = (0.1, 0.3)
CHARACTER_WARP_DY = (0.2, 0.3)
WORD_SPACE_PROBABILITY = 0.5
WORD_OFFSET_DX = 0.25
DEFAULT_WIDTH = 160
DEFAULT_HEIGHT = 60
DEFAULT_FONT_SIZES = (42, 50, 56)

# Global cache for loaded fonts
_truefonts_cache = []

def get_truefonts(fonts=None, font_sizes=None):
  global _truefonts_cache
  if _truefonts_cache: return _truefonts_cache
  fonts = fonts or DEFAULT_FONTS
  font_sizes = font_sizes or DEFAULT_FONT_SIZES
  _truefonts_cache = [
    truetype(n, s)
    for n in fonts
    for s in font_sizes
  ]
  return _truefonts_cache

def clear_fonts_cache():
    """Clear the fonts cache."""
    global _truefonts_cache
    _truefonts_cache = []

def create_noise_curve(image, color):
    """Add a random curve noise to the image."""
    w, h = image.size
    x1 = secrets.randbelow(int(w / 5) + 1)
    x2 = secrets.randbelow(w - int(w / 5) + 1) + int(w / 5)
    y1 = secrets.randbelow(h - 2 * int(h / 5) + 1) + int(h / 5)
    y2 = secrets.randbelow(h - y1 - int(h / 5) + 1) + y1
    points = [x1, y1, x2, y2]
    end = secrets.randbelow(41) + 160
    start = secrets.randbelow(21)
    Draw(image).arc(points, start, end, fill=color)
    return image

def create_noise_dots(image, color, width=3, number=30):
    """Add random dot noise to the image."""
    draw = Draw(image)
    w, h = image.size
    while number:
        x1 = secrets.randbelow(w + 1)
        y1 = secrets.randbelow(h + 1)
        draw.line(((x1, y1), (x1 - 1, y1 - 1)), fill=color, width=width)
        number -= 1
    return image

def draw_character(c, color, fonts=None, font_sizes=None):
    """Draw a single character with distortion effects."""
    truefonts = get_truefonts(fonts, font_sizes)
    font = secrets.choice(truefonts)
    
    # Create a temporary image to measure text
    temp_im = createImage('RGBA', (1, 1))
    temp_draw = Draw(temp_im)
    _, _, w, h = temp_draw.multiline_textbbox((1, 1), c, font=font)
    
    # Add random offset
    dx1 = secrets.randbelow(CHARACTER_OFFSET_DX[1] - CHARACTER_OFFSET_DX[0] + 1) + CHARACTER_OFFSET_DX[0]
    dy1 = secrets.randbelow(CHARACTER_OFFSET_DY[1] - CHARACTER_OFFSET_DY[0] + 1) + CHARACTER_OFFSET_DY[0]
    
    # Create image for the character
    im = createImage('RGBA', (int(w) + dx1, int(h) + dy1))
    Draw(im).text((dx1, dy1), c, font=font, fill=color)
    
    # Crop and rotate
    im = im.crop(im.getbbox())
    angle = CHARACTER_ROTATE[0] + (secrets.randbits(32) / (2**32)) * (CHARACTER_ROTATE[1] - CHARACTER_ROTATE[0])
    im = im.rotate(angle, Resampling.BILINEAR, expand=True)
    
    # Warp effect
    dx2 = w * (secrets.randbits(32) / (2**32)) * (CHARACTER_WARP_DX[1] - CHARACTER_WARP_DX[0]) + CHARACTER_WARP_DX[0]
    dy2 = h * (secrets.randbits(32) / (2**32)) * (CHARACTER_WARP_DY[1] - CHARACTER_WARP_DY[0]) + CHARACTER_WARP_DY[0]
    
    x1 = int(secrets.randbits(32) / (2**32) * (dx2 - (-dx2)) + (-dx2))
    y1 = int(secrets.randbits(32) / (2**32) * (dy2 - (-dy2)) + (-dy2))
    x2 = int(secrets.randbits(32) / (2**32) * (dx2 - (-dx2)) + (-dx2))
    y2 = int(secrets.randbits(32) / (2**32) * (dy2 - (-dy2)) + (-dy2))
    
    w2 = w + abs(x1) + abs(x2)
    h2 = h + abs(y1) + abs(y2)
    data = (
        x1, y1,
        -x1, h2 - y2,
        w2 + x2, h2 + y2,
        w2 - x2, -y1,
    )
    
    im = im.resize((w2, h2))
    im = im.transform((int(w), int(h)), Transform.QUAD, data)
    return im

def create_captcha_image(chars, color, background, width=None, height=None, fonts=None, font_sizes=None):
    """Create the CAPTCHA image with text."""
    width = width or DEFAULT_WIDTH
    height = height or DEFAULT_HEIGHT
    
    # Create background
    image = createImage('RGB', (width, height), background)
    draw = Draw(image)
    
    # Draw each character
    images = []
    for c in chars:
        if secrets.randbits(32) / (2**32) > WORD_SPACE_PROBABILITY:
            images.append(draw_character(" ", color, fonts, font_sizes))
        images.append(draw_character(c, color, fonts, font_sizes))
    
    # Calculate total text width
    text_width = sum([im.size[0] for im in images])
    
    # Resize if text is wider than image
    width = max(text_width, width)
    image = image.resize((width, height))
    
    # Position characters with random offsets
    average = int(text_width / len(chars))
    rand = int(WORD_OFFSET_DX * average)
    offset = int(average * 0.1)
    
    for im in images:
        w, h = im.size
        mask = im.convert('L').point(LOOKUP_TABLE)
        image.paste(im, (offset, int((height - h) / 2)), mask)
        offset = offset + w + (-secrets.randbelow(rand + 1))
    
    # Resize back to original width if needed
    if width > width:
        image = image.resize((width, height))
    
    return image

def random_color(start, end, opacity=None):
    """Generate a random color."""
    red = secrets.randbelow(end - start + 1) + start
    green = secrets.randbelow(end - start + 1) + start
    blue = secrets.randbelow(end - start + 1) + start
    if opacity is None:
        return red, green, blue
    return red, green, blue, opacity

def generate_captcha_image(chars, bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
    """Generate the complete CAPTCHA image."""
    background = bg_color if bg_color else random_color(238, 255)
    random_fg_color = random_color(10, 200, secrets.randbelow(36) + 220)
    color = fg_color if fg_color else random_fg_color
    
    im = create_captcha_image(chars, color, background, width, height, fonts, font_sizes)
    create_noise_dots(im, color)
    create_noise_curve(im, color)
    im = im.filter(SMOOTH)
    return im

def generate_captcha_bytes(chars, format='png', bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
    """Generate CAPTCHA and return as bytes."""
    im = generate_captcha_image(chars, bg_color, fg_color, width, height, fonts, font_sizes)
    out = BytesIO()
    im.save(out, format=format)
    out.seek(0)
    return out

def save_captcha(chars, output_path, format='png', bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
    """Generate and save CAPTCHA to file."""
    im = generate_captcha_image(chars, bg_color, fg_color, width, height, fonts, font_sizes)
    im.save(output_path, format=format)


# Example usage
if __name__ == "__main__": 
    captcha_image = generate_captcha_image("R4B6N3")
    captcha_image.show()
