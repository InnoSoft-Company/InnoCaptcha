import os, secrets, sqlite3, threading
from PIL.ImageFilter import SMOOTH
from PIL import Image, ImageFont
from PIL.Image import Resampling
from PIL.ImageDraw import Draw
from . import utils

default_font = ImageFont.truetype(os.path.join(os.path.abspath(os.path.dirname(__file__)), f'data/fonts/{secrets.choice([f for f in os.listdir(os.path.join(os.path.abspath(os.path.dirname(__file__)), "data/fonts")) if f.endswith(".ttf")])}'), 40)
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

class TextCaptcha():
  def __init__(self, chars=None, color=(0, 0, 0), background=(255, 255, 255), width=300, height=80):
    base = secrets.randbelow(101) + 80
    shift = (secrets.randbelow(56) + 45) * (1 - 2 * secrets.randbelow(2))
    self.background = (base, secrets.randbelow(101) + 80, secrets.randbelow(101) + 80)
    self.text_color = tuple(max(0, min(255, c + shift)) for c in self.background)
    self.image_width = width
    self.image_height = height
    self.id = None
    self.image = None
    self.draw = None
    self.chars = chars
    self.char_images = []
    threading.Thread(target=self.cleanup, daemon=True).start()
    
  def cleanup(self):
    db = utils.DB(db_path)
    db.execute("DELETE FROM text WHERE expires_at < datetime('now')")
    db.commit()

  def create(self, chars=None):
    self.char_images.clear()
    self.image = Image.new('RGB', (self.image_width, self.image_height), self.background)
    self.draw = Draw(self.image)
    self.id = secrets.token_hex(16)
    if not chars: chars = [secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)]
    self.chars = "".join(chars[0:6])
    db = utils.DB(db_path)
    db.execute("INSERT INTO text (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, self.chars))
    for char in self.chars:
      temp_image = Image.new('RGBA', (1, 1))
      temp_draw = Draw(temp_image)
      left, top, w, h = temp_draw.multiline_textbbox((1, 1), char, font=default_font)          
      im = Image.new('RGBA', (int(w), int(h)))
      Draw(im).text((0, 0), char, font=default_font, fill=self.text_color)   
      im = im.crop(im.getbbox())    
      angle = -45 + (secrets.randbits(32) / (2**32)) * (45 - (-45))
      im = im.rotate(angle, Resampling.BILINEAR, expand=True)
      self.char_images.append(im)
    for dot in range(30):
      x1 = secrets.randbelow(self.image_width)
      y1 = secrets.randbelow(self.image_height)
      self.draw.line(((x1, y1), (x1 - 1, y1 - 1)), width=3, fill=self.text_color)
    for curve in range(10):
      x1 = secrets.randbelow(self.image_width)
      y1 = secrets.randbelow(self.image_height)
      x2 = secrets.randbelow(self.image_width)
      y2 = secrets.randbelow(self.image_height)
      start = secrets.randbelow(360)
      end = start + secrets.randbelow(360 - start)        
      x0 = min(x1, x2)
      y0 = min(y1, y2)
      x1 = max(x1, x2)
      y1 = max(y1, y2)
      self.draw.arc(((x0, y0), (x1, y1)), start, end, fill=self.text_color, width=3)
    x = 0
    for im in self.char_images:
      self.image.paste(im, (x, (self.image_height - im.size[1]) // 2), im)
      x += im.size[0] + int(self.image_width * 0.05)
    self.image = self.image.filter(SMOOTH)
    db.commit()

  def save(self, path):
    if self.image is None:
      raise ValueError("No captcha created.")
      return False
    self.image.save(path)

  def verify(self, user_input):
    db = utils.DB(db_path)
    if not self.id:
      db.commit()
      raise RuntimeError("Captcha not created")
      return False
    db.execute("SELECT answer, attempts, expires_at FROM text WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5", (self.id,))
    result = db.fetchone()
    if not result:
      db.commit()
      raise RuntimeError("You have reached the maximum number of attempts or the captcha has expired.")
      return False
    answer, attempts, expires_at = result
    if secrets.compare_digest(user_input, answer):
      db.execute("DELETE FROM text WHERE id = ?", (self.id,))
      db.commit()
      return True
    else:
      db.execute("UPDATE text SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      db.commit()
      return False
