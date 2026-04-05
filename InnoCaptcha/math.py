from PIL import Image, ImageDraw, ImageFont
import random, sqlite3, os, threading, sqlite3, secrets
from . import utils

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

class MathCaptcha:
  def __init__(self, id=None, question=None, answer=None, output="text"):
    if output not in ("text", "image"):
      raise ValueError("output must be 'text' or 'image'")
    self.output = output
    generated = self.generate()
    self.question, self.answer = generated.values()
    if self.output == "image":
      self._render_image()
    threading.Thread(target=self.cleanup, daemon=True).start()

  def _render_image(self):
    text = f"{self.question} = ?"
    try:
        font_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data/fonts")
        font_file = secrets.choice([f for f in os.listdir(font_dir) if f.endswith(".ttf")])
        font = ImageFont.truetype(os.path.join(font_dir, font_file), 40)
    except Exception:
        font = ImageFont.load_default()
    
    dummy_img = Image.new('RGB', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 40
    height = bbox[3] - bbox[1] + 40
    
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((20, 20), text, fill=(0, 0, 0), font=font)
    self.image = img

  def generate(self):
    db = utils.DB(db_path)
    self.id = secrets.token_hex(16)
    while True:
      question = f'{random.randint(1, 10)}{random.choice(["+", "-", "*", "/"])}{random.randint(1, 10)}'
      answer = str(eval(question))
      if "." not in str(answer): break
    db.execute("INSERT INTO math (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, answer))
    db.commit()
    return {"question": question, "answer": answer}

  def get_question(self):
    if self.output == "image":
      return self.image
    return f"{self.question} = ?"

  def verify(self, user_answer):
    db = utils.DB(db_path)
    if not self.id:
      db.conn.close()
      raise RuntimeError("Captcha not created")
    db.cursor.execute("SELECT answer, attempts, expires_at FROM math WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5", (self.id,))
    result = db.cursor.fetchone()
    if not result:
      db.conn.close()
      raise RuntimeError("Captcha not found or expired")
    answer, attempts, expires_at = result
    if secrets.compare_digest(str(answer), str(user_answer)):
      db.cursor.execute("DELETE FROM math WHERE id = ?", (self.id,))
      db.conn.commit()
      db.conn.close()
      return True
    db.cursor.execute("UPDATE math SET attempts = attempts + 1 WHERE id = ?", (self.id,))
    db.conn.commit()
    db.conn.close()
    return False

  def cleanup(self):
    local_conn = utils.DB(db_path)
    local_conn.execute("DELETE FROM math WHERE expires_at < datetime('now')")
    local_conn.commit()