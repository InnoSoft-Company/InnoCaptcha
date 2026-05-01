from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.Image import Resampling, Transform
import math, os, secrets, threading, operator, random
from .utils import DB, log_event, DB_PATH
from cryptography.fernet import Fernet

font_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data/fonts")

class MathCaptcha:
  def __init__(self, output="text", lang='en'):
    if output not in ("text", "image"): raise ValueError("output must be 'text' or 'image'")
    self.output = output
    self.lang = lang
    self.question = None
    self.answer = None
    self.id = None
    self.image = None
    self.create() # Backward compatibility
    threading.Thread(target=self.cleanup, daemon=True).start()

  def _load_font(self, size):
    try:
      font_files = [f for f in os.listdir(font_dir) if f.endswith(".ttf")]
      if font_files: return ImageFont.truetype(os.path.join(font_dir, secrets.choice(font_files)), size)
    except Exception: pass
    return ImageFont.load_default()

  def _text_bbox(self, text, font): return ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=font)

  def _tokenize_question(self):
    tokens, current = [], []
    for char in self.question:
      if char.isdigit():
        current.append(char)
        continue
      if current:
        tokens.append("".join(current))
        current.clear()
      tokens.append(char)
    if current: tokens.append("".join(current))
    tokens.extend(["=", "?"])
    return tokens

  def _build_palette(self): 
    return {
      "background": (235 + secrets.randbelow(16), 235 + secrets.randbelow(16), 235 + secrets.randbelow(16)), 
      "text": (15 + secrets.randbelow(45), 15 + secrets.randbelow(45) + secrets.randbelow(20), 15 + secrets.randbelow(45) + secrets.randbelow(20)), 
      "noise": (135 + secrets.randbelow(45), 135 + secrets.randbelow(45), 135 + secrets.randbelow(45))
    }

  def _render_token(self, token, palette):
    font = self._load_font(36 + secrets.randbelow(8))
    bbox = self._text_bbox(token, font)
    width = max(1, (bbox[2] - bbox[0]) + 24)
    height = max(1, (bbox[3] - bbox[1]) + 24)
    token_image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    token_draw = ImageDraw.Draw(token_image)
    token_color = tuple(max(0, min(255, channel + secrets.randbelow(30) - 15)) for channel in palette["text"])
    token_draw.text((12 - bbox[0], 12 - bbox[1]), token, fill=token_color + (255,), font=font)
    shear = (secrets.randbelow(25) - 12) / 100
    xshift = int(abs(shear) * token_image.height)
    token_image = token_image.transform((token_image.width + xshift, token_image.height), Transform.AFFINE, (1, shear, -xshift if shear > 0 else 0, 0, 1, 0), resample=Resampling.BICUBIC)
    angle = 0 if token in ["+", "-", "×", "="] else secrets.randbelow(31) - 15
    token_image = token_image.rotate(angle, resample=Resampling.BICUBIC, expand=True)
    scale = 0.4 + (secrets.randbelow(20) / 100.0)
    small_size = (max(1, int(token_image.width * scale)), max(1, int(token_image.height * scale)))
    pixelated = token_image.resize(small_size, resample=Resampling.BILINEAR)
    return pixelated.resize(token_image.size, resample=Resampling.NEAREST)

  def _draw_interference(self, image, palette):
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size

    for _ in range(max(70, (width * height) // 220)):
      x = secrets.randbelow(width)
      y = secrets.randbelow(height)
      radius = secrets.randbelow(2) + 1
      color = tuple(min(255, channel + secrets.randbelow(30)) for channel in palette["background"])
      draw.ellipse((x, y, x + radius, y + radius), fill=color + (55,))

    for _ in range(4):
      x1 = secrets.randbelow(width)
      y1 = secrets.randbelow(height)
      x2 = secrets.randbelow(width)
      y2 = secrets.randbelow(height)
      start = secrets.randbelow(181)
      end = min(359, start + 90 + secrets.randbelow(180))
      left, right = sorted((x1, x2))
      top, bottom = sorted((y1, y2))
      if left == right: right += 1
      if top == bottom: bottom += 1
      curve_color = tuple(max(0, min(255, channel + secrets.randbelow(30) - 15)) for channel in palette["noise"])
      draw.arc((left, top, right, bottom), start, end, fill=curve_color + (95,), width=1)
    return Image.alpha_composite(image.convert("RGBA"), overlay)

  def _apply_wave_distortion(self, image, background):
    width, height = image.size
    pad = 10
    expanded = Image.new("RGBA", (width + pad * 2, height + pad * 2), background + (255,))
    expanded.paste(image, (pad, pad), image)
    horizontal = Image.new("RGBA", expanded.size, background + (255,))
    amplitude_x = 3 + secrets.randbelow(4)
    frequency_x = 0.08 + (secrets.randbelow(80) / 1000.0)
    phase_x = (secrets.randbelow(200) / 100.0) * math.pi
    for y in range(expanded.height):
      offset = int(round(amplitude_x * math.sin((y * frequency_x) + phase_x)))
      row = expanded.crop((0, y, expanded.width, y + 1))
      horizontal.paste(row, (offset, y))
    vertical = Image.new("RGBA", horizontal.size, background + (255,))
    amplitude_y = 2 + secrets.randbelow(4)
    frequency_y = 0.08 + (secrets.randbelow(60) / 1000.0)
    phase_y = (secrets.randbelow(200) / 100.0) * math.pi
    for x in range(horizontal.width):
      offset = int(round(amplitude_y * math.sin((x * frequency_y) + phase_y)))
      column = horizontal.crop((x, 0, x + 1, horizontal.height))
      vertical.paste(column, (x, offset))
    return vertical.crop((pad, pad, pad + width, pad + height)).convert("RGB")

  def create(self, ip=None, session_id=None):
    self.id = secrets.token_hex(16)
    operators = {"+": operator.add, "-": operator.sub, "×": operator.mul}
    op = secrets.choice(["+", "-", "×"])
    num1 = secrets.randbelow(10) + 1
    num2 = secrets.randbelow(10) + 1
    if op == "-" and num1 < num2: num1, num2 = num2, num1
    self.question = f'{num1}{op}{num2}'
    self.answer = str(operators[op](num1, num2))
    
    with DB(db_path=DB_PATH) as db:
      # Get encryption key for session binding
      db.execute("SELECT value FROM encryption_key LIMIT 1")
      key = db.fetchone()
      if key:
        key = key[0]
        fernet = Fernet(key)
        self.answer = fernet.encrypt(self.answer.encode())
      db.execute("INSERT INTO math (id, answer, attempts, ip_address, session_id, created_at, expires_at) VALUES (?, ?, 0, ?, ?, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, self.answer, ip, session_id))
      db.commit()
    
    log_event("CAPTCHA_CREATED", f"Math captcha created: {self.id}", {"module": "math", "ip": ip, "session": session_id})
    if self.output == "image": self._render_image()
    return self.id

  def _render_image(self):
    palette = self._build_palette()
    token_images = [self._render_token(token, palette) for token in self._tokenize_question()]
    max_height = max(token.height for token in token_images)
    margins, gap, x = 20, 10, 20
    width = sum(token.width for token in token_images) + (len(token_images) - 1) * gap + (margins * 2)
    height = max(max_height + 36, 86)
    image = Image.new("RGBA", (width, height), palette["background"] + (255,))
    baseline = (height - max_height) // 2
    for index, token_image in enumerate(token_images):
      y = max(6, min(height - token_image.height - 6, baseline + secrets.randbelow(9) - 4))
      image.alpha_composite(token_image, (x, y))
      extra_gap = 8 if token_image.width > 28 else 0
      if index >= len(token_images) - 2: extra_gap += 4
      x += token_image.width + gap + extra_gap
    image = self._draw_interference(image, palette)
    image = self._apply_wave_distortion(image, palette["background"])
    self.image = image.filter(ImageFilter.SMOOTH)

  def get_question(self):
    if self.output == "image": return self.image
    return f"{self.question} = ?"

  def verify(self, user_answer, ip=None, session_id=None):
    if not self.id:
      raise RuntimeError("Captcha not created" if self.lang == 'en' else "لم يتم إنشاء الكابتشا")
      
    with DB(DB_PATH) as db:
      db.execute("SELECT answer, attempts, expires_at, ip_address, session_id FROM math WHERE id = ?", (self.id,))
      result = db.fetchone()
      if not result:
        log_event("VERIFY_ABORT", f"Captcha not found: {self.id}", {"module": "math", "ip": ip})
        return "Captcha not found" if self.lang == 'en' else "الكابتشا غير موجودة"
      
      answer, attempts, expires_at, db_ip, db_session = result
      
      # Get encryption key for session binding
      db.execute("SELECT value FROM encryption_key LIMIT 1")
      key = db.fetchone()
      if key:
        fernet = Fernet(key[0])
        try:
          answer = fernet.decrypt(answer).decode()
        except Exception:
          log_event("DECRYPT_ERROR", f"Failed to decrypt answer for {self.id}", {"module": "math"})
          return "Captcha verification error" if self.lang == 'en' else "خطأ في التحقق"
        answer = fernet.decrypt(answer).decode()
        
      # Context Binding Validation (#5)
      if (db_ip and ip and db_ip != ip) or (db_session and session_id and db_session != session_id):
        log_event("VERIFY_REJECTED", f"Context mismatch for {self.id}", {"module": "math", "ip": ip, "db_ip": db_ip})
        return "Security context mismatch" if self.lang == 'en' else "خطأ في التحقق من المصدر"

      # Rate Limiting & Expiry (#4)
      if attempts >= 5:
        log_event("VERIFY_REJECTED", f"Max attempts reached: {self.id}", {"module": "math", "ip": ip})
        return "Max attempts reached" if self.lang == 'en' else "تجاوزت عدد المحاولات"
      
      # Expiry check logic (DB might return expired)
      db.execute("SELECT 1 FROM math WHERE id = ? AND expires_at >= datetime('now')", (self.id,))
      if not db.fetchone():
        log_event("VERIFY_REJECTED", f"Captcha expired: {self.id}", {"module": "math", "ip": ip})
        return "Captcha expired" if self.lang == 'en' else "انتهت صلاحية الكابتشا"

      if secrets.compare_digest(str(answer), str(user_answer)):
        db.execute("DELETE FROM math WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_SUCCESS", f"Captcha verified: {self.id}", {"module": "math", "ip": ip})
        return True
        
      db.execute("UPDATE math SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      db.commit()
      log_event("VERIFY_FAILED", f"Wrong answer for {self.id}", {"module": "math", "ip": ip, "attempt": attempts+1})
    return False

  def cleanup(self):
    with DB(DB_PATH) as db:
      db.execute("DELETE FROM math WHERE expires_at < datetime('now')")
      db.commit()
