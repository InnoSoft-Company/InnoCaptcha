import random, sqlite3, os, threading, sqlite3, secrets
from . import utils

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'dbs/captcha.db')

class MathCaptcha:
  def __init__(self, id=None, question=None, answer=None):
    generated = self.generate()
    self.question, self.answer = generated.values()
    threading.Thread(target=self.cleanup, daemon=True).start()

  def generate(self):
    db = utils.DB(db_path)
    self.id = secrets.token_hex(16)
    while True:
      question = f'{random.randint(1, 10)}{random.choice(["+", "-", "*", "/"])}{random.randint(1, 10)}'
      answer = str(eval(question))
      if "." not in str(answer): break
    db.cursor.execute("INSERT INTO math (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, answer))
    db.conn.commit()
    db.conn.close()
    return {"question": question, "answer": answer}

  def get_question(self): return f"{self.question} = ?"

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
    local_conn = sqlite3.connect(db_path)
    local_cursor = local_conn.cursor()
    local_cursor.execute("DELETE FROM math WHERE expires_at < datetime('now')")
    local_conn.commit()
    local_conn.close()
