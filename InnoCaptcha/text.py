from .utils import DB, DB_PATH, log_event, get_encryption_key
from cryptography.fernet import Fernet
from bidi.algorithm import get_display
from PIL.ImageFilter import SMOOTH
from PIL.Image import Resampling
from PIL import Image, ImageFont
import os, secrets, threading, logging
from PIL.ImageDraw import Draw
import arabic_reshaper

font_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data/fonts")

def get_font(size=40):
  try:
    fonts = sorted([f for f in os.listdir(font_dir) if f.endswith(".ttf")])
    if fonts: return ImageFont.truetype(os.path.join(font_dir, secrets.choice(fonts)), size)
  except Exception as e: logging.warning(f"Could not load font: {e}")
  return ImageFont.load_default()

class TextCaptcha():
  def __init__(self, color=None, background=None, width=300, height=80, lang='en'):
    self.lang = lang
    if color and background:
      self.text_color = color
      self.background = background
    else:
      base = secrets.randbelow(101) + 80
      shift = (secrets.randbelow(56) + 45) * (1 - 2 * secrets.randbelow(2))
      self.background = (base, secrets.randbelow(101) + 80, secrets.randbelow(101) + 80)
      self.text_color = tuple(max(0, min(255, c + shift)) for c in self.background)
    self.image_width = width
    self.image_height = height
    self.id = None
    self.image = None
    self.draw = None
    self.chars = None
    self.char_images = []
    
  def cleanup(self):
    with DB(db_path=DB_PATH) as db:
      db.execute("DELETE FROM text WHERE expires_at < datetime('now')")
      db.commit()

  def create(self, chars=None, ip=None, session_id=None):
    self.cleanup()
    self.char_images.clear()
    self.image = Image.new('RGB', (self.image_width, self.image_height), self.background)
    self.draw = Draw(self.image)
    self.id = secrets.token_hex(16)
    if not chars: chars = [secrets.choice('abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)]
    self.chars = "".join(chars[0:6])
    key = get_encryption_key()
    fernet = Fernet(key)
    db_answer = fernet.encrypt(self.chars.encode())
    with DB(db_path=DB_PATH) as db:
      db.execute("INSERT INTO text (id, answer, attempts, ip_address, session_id, created_at, expires_at) VALUES (?, ?, 0, ?, ?, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))",  (self.id, db_answer, ip, session_id))
      db.commit()
    log_event("CAPTCHA_CREATED", f"Text captcha created: {self.id}", {"module": "text", "ip": ip, "session": session_id})
    font = get_font(40)
    display_text = self.chars
    if self.lang == 'ar':
      reshaped_text = arabic_reshaper.reshape(self.chars)
      display_text = get_display(reshaped_text)
    for char in display_text:
      temp_image = Image.new('RGBA', (1, 1))
      temp_draw = Draw(temp_image)
      try: left, top, w, h = temp_draw.multiline_textbbox((0, 0), char, font=font)
      except AttributeError: w, h = font.getsize(char)
          
      im = Image.new('RGBA', (max(1, int(w)), max(1, int(h))))
      Draw(im).text((0, 0), char, font=font, fill=self.text_color)   
      im = im.crop(im.getbbox()) if im.getbbox() else im
      
      angle = -45 + (secrets.randbits(32) / (2**32)) * 90
      im = im.rotate(angle, Resampling.BILINEAR, expand=True)
      self.char_images.append(im)
      
    # Add noise
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
      end = start + secrets.randbelow(max(1, 360 - start))        
      x0, x1 = (x1, x2) if x1 < x2 else (x2, x1)
      y0, y1 = (y1, y2) if y1 < y2 else (y2, y1)
      self.draw.arc(((x0, y0), (max(x0+1, x1), max(y0+1, y1))), start, end, fill=self.text_color, width=3)
      
    x = 10
    for im in self.char_images:
      self.image.paste(im, (x, (self.image_height - im.size[1]) // 2), im)
      x += im.size[0] + int(self.image_width * 0.05)
    self.chars = None  # Remove plaintext answer from memory
    return self.id

  def save(self, path):
    if self.image is None: raise ValueError("No captcha created.")
    path = os.path.realpath(path)
    if not path.endswith(('.png', '.jpg')): raise ValueError("Invalid file extension. Must be .png or .jpg")
    self.image.save(path)

  def verify(self, user_input, ip=None, session_id=None):
    if not self.id: raise RuntimeError("Captcha not created" if self.lang == 'en' else "لم يتم إنشاء الكابتشا")
    with DB(db_path=DB_PATH) as db:
      db.execute("SELECT answer, attempts, expires_at, ip_address, session_id FROM text WHERE id = ?", (self.id,))
      result = db.fetchone()
      if not result:
        log_event("VERIFY_ABORT", f"Captcha not found: {self.id}", {"module": "text", "ip": ip})
        return "Captcha not found" if self.lang == 'en' else "الكابتشا غير موجودة"
          
      answer, attempts, expires_at, db_ip, db_session = result
      
      key = get_encryption_key()
      fernet = Fernet(key)
      try:
        answer = fernet.decrypt(answer).decode()
      except Exception:
        log_event("DECRYPT_ERROR", f"Failed to decrypt answer for {self.id}", {"module": "text"})
        return "Captcha verification error" if self.lang == 'en' else "خطأ في التحقق"

      # Context Binding Validation
      ip_match = not db_ip or secrets.compare_digest(db_ip, ip or "")
      session_match = not db_session or secrets.compare_digest(db_session, session_id or "")
      if not ip_match or not session_match:
        log_event("VERIFY_REJECTED", f"Context mismatch for {self.id}", {"module": "text", "ip": ip, "db_ip": db_ip})
        return "Security context mismatch" if self.lang == 'en' else "خطأ في التحقق من المصدر"

      # Rate Limiting & Expiry
      if attempts >= 5:
        log_event("VERIFY_REJECTED", f"Max attempts reached: {self.id}", {"module": "text", "ip": ip})
        return "Max attempts reached" if self.lang == 'en' else "تجاوزت عدد المحاولات"

      db.execute("SELECT 1 FROM text WHERE id = ? AND expires_at >= datetime('now')", (self.id,))
      if not db.fetchone():
        log_event("VERIFY_REJECTED", f"Captcha expired: {self.id}", {"module": "text", "ip": ip})
        return "Captcha expired" if self.lang == 'en' else "انتهت صلاحية الكابتشا"
      # Normalize input for comparison
      user_input = str(user_input).strip().lower()
      answer = str(answer).strip().lower()

      if secrets.compare_digest(user_input, answer):
        db.execute("DELETE FROM text WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_SUCCESS", f"Captcha verified: {self.id}", {"module": "text", "ip": ip})
        return True
      else:
        db.execute("UPDATE text SET attempts = attempts + 1 WHERE id = ? AND attempts < 5", (self.id,))
        db.commit()
        log_event("VERIFY_FAILED", f"Wrong answer for {self.id}", {"module": "text", "ip": ip, "attempt": attempts+1})
    return False
