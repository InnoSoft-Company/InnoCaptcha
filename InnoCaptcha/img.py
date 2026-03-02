import os, secrets, uuid, typing as t
from io import BytesIO
from PIL.Image import new as createImage, Transform, Resampling
from PIL.ImageDraw import Draw
from PIL.ImageFont import truetype
from PIL.ImageFilter import SMOOTH

ColorTuple = t.Union[t.Tuple[int, int, int], t.Tuple[int, int, int, int]]

# -------------------------------
# CONFIGURATION
# -------------------------------
class CaptchaConfig:
  DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)))
  DEFAULT_FONTS = [os.path.join(DATA_DIR, 'DroidSansMono.ttf')]
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

# -------------------------------
# FONTS HANDLING
# -------------------------------
_truefonts_cache = []

def get_truefonts(fonts=None, font_sizes=None):
  global _truefonts_cache
  if _truefonts_cache:
      return _truefonts_cache
  fonts = fonts or CaptchaConfig.DEFAULT_FONTS
  font_sizes = font_sizes or CaptchaConfig.DEFAULT_FONT_SIZES
  _truefonts_cache = [truetype(f, s) for f in fonts for s in font_sizes]
  return _truefonts_cache

def clear_fonts_cache():
  global _truefonts_cache
  _truefonts_cache = []

# -------------------------------
# NOISE FUNCTIONS
# -------------------------------
def create_noise_curve(image, color):
  w, h = image.size
  x1 = secrets.randbelow(int(w / 5) + 1)
  x2 = secrets.randbelow(w - int(w / 5) + 1) + int(w / 5)
  y1 = secrets.randbelow(h - 2 * int(h / 5) + 1) + int(h / 5)
  y2 = secrets.randbelow(h - y1 - int(h / 5) + 1) + y1
  points = [x1, y1, x2, y2]
  start, end = secrets.randbelow(21), secrets.randbelow(41) + 160
  Draw(image).arc(points, start, end, fill=color)
  return image

def create_noise_dots(image, color, width=3, number=30):
  draw = Draw(image)
  w, h = image.size
  for _ in range(number):
      x1, y1 = secrets.randbelow(w), secrets.randbelow(h)
      draw.line(((x1, y1), (x1 - 1, y1 - 1)), fill=color, width=width)
  return image

# -------------------------------
# CHARACTER DRAWING
# -------------------------------
def draw_character(c, color, fonts=None, font_sizes=None):
  truefonts = get_truefonts(fonts, font_sizes)
  font = secrets.choice(truefonts)

  temp_im = createImage('RGBA', (1, 1))
  temp_draw = Draw(temp_im)
  _, _, w, h = temp_draw.multiline_textbbox((1, 1), c, font=font)

  dx1 = secrets.randbelow(CaptchaConfig.CHARACTER_OFFSET_DX[1] - CaptchaConfig.CHARACTER_OFFSET_DX[0] + 1) + CaptchaConfig.CHARACTER_OFFSET_DX[0]
  dy1 = secrets.randbelow(CaptchaConfig.CHARACTER_OFFSET_DY[1] - CaptchaConfig.CHARACTER_OFFSET_DY[0] + 1) + CaptchaConfig.CHARACTER_OFFSET_DY[0]

  im = createImage('RGBA', (int(w) + dx1, int(h) + dy1))
  Draw(im).text((dx1, dy1), c, font=font, fill=color)

  im = im.crop(im.getbbox())
  angle = CaptchaConfig.CHARACTER_ROTATE[0] + (secrets.randbits(32)/(2**32)) * (CaptchaConfig.CHARACTER_ROTATE[1]-CaptchaConfig.CHARACTER_ROTATE[0])
  im = im.rotate(angle, Resampling.BILINEAR, expand=True)

  dx2 = w * (secrets.randbits(32)/(2**32)) * (CaptchaConfig.CHARACTER_WARP_DX[1]-CaptchaConfig.CHARACTER_WARP_DX[0]) + CaptchaConfig.CHARACTER_WARP_DX[0]
  dy2 = h * (secrets.randbits(32)/(2**32)) * (CaptchaConfig.CHARACTER_WARP_DY[1]-CaptchaConfig.CHARACTER_WARP_DY[0]) + CaptchaConfig.CHARACTER_WARP_DY[0]

  x1 = int(secrets.randbits(32)/(2**32)*(dx2-(-dx2)) + (-dx2))
  y1 = int(secrets.randbits(32)/(2**32)*(dy2-(-dy2)) + (-dy2))
  x2 = int(secrets.randbits(32)/(2**32)*(dx2-(-dx2)) + (-dx2))
  y2 = int(secrets.randbits(32)/(2**32)*(dy2-(-dy2)) + (-dy2))

  w2, h2 = w + abs(x1) + abs(x2), h + abs(y1) + abs(y2)
  data = (x1, y1, -x1, h2 - y2, w2 + x2, h2 + y2, w2 - x2, -y1)

  im = im.resize((w2, h2))
  im = im.transform((int(w), int(h)), Transform.QUAD, data)
  return im

# -------------------------------
# UTILS
# -------------------------------
def random_color(start, end, opacity=None):
  r = secrets.randbelow(end-start+1)+start
  g = secrets.randbelow(end-start+1)+start
  b = secrets.randbelow(end-start+1)+start
  return (r, g, b) if opacity is None else (r, g, b, opacity)

# -------------------------------
# CAPTCHA GENERATION
# -------------------------------
def create_captcha_image(chars, color, background, width=None, height=None, fonts=None, font_sizes=None):
  width, height = width or CaptchaConfig.DEFAULT_WIDTH, height or CaptchaConfig.DEFAULT_HEIGHT
  image = createImage('RGB', (width, height), background)

  images = []
  for c in chars:
      if secrets.randbits(32)/(2**32) > CaptchaConfig.WORD_SPACE_PROBABILITY:
          images.append(draw_character(" ", color, fonts, font_sizes))
      images.append(draw_character(c, color, fonts, font_sizes))

  text_width = sum([im.size[0] for im in images])
  offset = int(text_width * 0.1)
  for im in images:
      w, h = im.size
      mask = im.convert('L').point(CaptchaConfig.LOOKUP_TABLE)
      image.paste(im, (offset, int((height-h)/2)), mask)
      offset += w + (-secrets.randbelow(int(CaptchaConfig.WORD_OFFSET_DX*text_width)+1))

  return image

def generate_captcha_image(chars, bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
  background = bg_color if bg_color else random_color(238, 255)
  color = fg_color if fg_color else random_color(10, 200, secrets.randbelow(36)+220)

  im = create_captcha_image(chars, color, background, width, height, fonts, font_sizes)
  create_noise_dots(im, color)
  create_noise_curve(im, color)
  im = im.filter(SMOOTH)
  return im

def generate_captcha_bytes(chars, format='png', bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
  im = generate_captcha_image(chars, bg_color, fg_color, width, height, fonts, font_sizes)
  out = BytesIO()
  im.save(out, format=format)
  out.seek(0)
  return out

def save_captcha(chars, path="captcha.png", format='png', bg_color=None, fg_color=None, width=None, height=None, fonts=None, font_sizes=None):
  im = generate_captcha_image(chars, bg_color, fg_color, width, height, fonts, font_sizes)
  im.save(path, format=format)

# -------------------------------
# Example
# -------------------------------
if __name__ == "__main__":
  save_captcha("6Hsvf4")