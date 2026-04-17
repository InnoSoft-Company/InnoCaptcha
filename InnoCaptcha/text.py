from .utils import DB, DB_PATH, log_event
from cryptography.fernet import Fernet
from bidi.algorithm import get_display
from PIL.ImageFilter import SMOOTH
from PIL.Image import Resampling
from PIL import Image, ImageFont
import os, secrets, threading
from PIL.ImageDraw import Draw
import arabic_reshaper

font_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data/fonts")

def get_font(size=40):
  try:
    fonts = sorted([f for f in os.listdir(font_dir) if f.endswith(".ttf")])
    if fonts:
      return ImageFont.truetype(os.path.join(font_dir, secrets.choice(fonts)), size)
  except Exception:
    pass
  return ImageFont.load_default()

class TextCaptcha():
  def __init__(self, color=(0, 0, 0), background=(255, 255, 255), width=300, height=80, lang='en'):
    self.lang = lang
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
    threading.Thread(target=self.cleanup, daemon=True).start()
    
  def cleanup(self):
    with DB(db_path=DB_PATH) as db:
      db.execute("DELETE FROM text WHERE expires_at < datetime('now')")
      db.commit()

  def create(self, chars=None, ip=None, session_id=None):
    self.char_images.clear()
    self.image = Image.new('RGB', (self.image_width, self.image_height), self.background)
    self.draw = Draw(self.image)
    self.id = secrets.token_hex(16)
    
    if not chars: 
      chars = [secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)]
    self.chars = "".join(chars[0:6])
    
    with DB(db_path=DB_PATH) as db:
      db.execute("SELECT value FROM encryption_key limit 1")
      key = db.fetchone()
      if key:
        fernet = Fernet(key[0])
        self.chars = fernet.encrypt(self.chars.encode())
      db.execute("INSERT INTO text (id, answer, attempts, ip_address, session_id, created_at, expires_at) VALUES (?, ?, 0, ?, ?, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))",  (self.id, self.chars, ip, session_id))
      db.commit()

    log_event("CAPTCHA_CREATED", f"Text captcha created: {self.id}", {"module": "text", "ip": ip, "session": session_id})
        
    font = get_font(40)
    
    # RTL support for Arabic
    display_text = self.chars
    if self.lang == 'ar':
      reshaped_text = arabic_reshaper.reshape(self.chars)
      display_text = get_display(reshaped_text)
        
    for char in display_text:
      temp_image = Image.new('RGBA', (1, 1))
      temp_draw = Draw(temp_image)
      try:
        left, top, w, h = temp_draw.multiline_textbbox((0, 0), char, font=font)
      except AttributeError:
        w, h = font.getsize(char)
          
      im = Image.new('RGBA', (max(1, int(w)), max(1, int(h))))
      Draw(im).text((0, 0), char, font=font, fill=self.text_color)   
      im = im.crop(im.getbbox()) if im.getbbox() else im
      
      angle = -45 + (secrets.randbits(32) / (2**32)) * 90
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
      end = start + secrets.randbelow(max(1, 360 - start))        
      x0, x1 = (x1, x2) if x1 < x2 else (x2, x1)
      y0, y1 = (y1, y2) if y1 < y2 else (y2, y1)
      self.draw.arc(((x0, y0), (max(x0+1, x1), max(y0+1, y1))), start, end, fill=self.text_color, width=3)
      
    x = 10
    for im in self.char_images:
      self.image.paste(im, (x, (self.image_height - im.size[1]) // 2), im)
      x += im.size[0] + int(self.image_width * 0.05)
    self.image = self.image.filter(SMOOTH)
    return self.id

  def save(self, path):
    if self.image is None: raise ValueError("No captcha created.")
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
      
      db.execute("SELECT value FROM encryption_key limit 1")
      key = db.fetchone()
      if key:
        fernet = Fernet(key[0])
        answer = fernet.decrypt(answer)
        
      # Context Binding Validation (#5)
      if (db_ip and ip and db_ip != ip) or (db_session and session_id and db_session != session_id):
        log_event("VERIFY_REJECTED", f"Context mismatch for {self.id}", {"module": "text", "ip": ip, "db_ip": db_ip})
        return "Security context mismatch" if self.lang == 'en' else "خطأ في التحقق من المصدر"

      # Rate Limiting & Expiry (#4)
      if attempts >= 5:
        log_event("VERIFY_REJECTED", f"Max attempts reached: {self.id}", {"module": "text", "ip": ip})
        return "Max attempts reached" if self.lang == 'en' else "تجاوزت عدد المحاولات"

      db.execute("SELECT 1 FROM text WHERE id = ? AND expires_at >= datetime('now')", (self.id,))
      if not db.fetchone():
        log_event("VERIFY_REJECTED", f"Captcha expired: {self.id}", {"module": "text", "ip": ip})
        return "Captcha expired" if self.lang == 'en' else "انتهت صلاحية الكابتشا"

      if secrets.compare_digest(user_input, answer):
        db.execute("DELETE FROM text WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_SUCCESS", f"Captcha verified: {self.id}", {"module": "text", "ip": ip})
        return True
      else:
        db.execute("UPDATE text SET attempts = attempts + 1 WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_FAILED", f"Wrong answer for {self.id}", {"module": "text", "ip": ip, "attempt": attempts+1})
    return False
