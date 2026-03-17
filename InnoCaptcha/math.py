import random, sqlite3, os, threading, sqlite3, secrets

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'captcha.db')

class MathCaptcha:
  def __init__(self, id=None, question=None, answer=None):
    generated = self.generate()
    self.question, self.answer = generated.values()
    threading.Thread(target=self.cleanup, daemon=True).start()
  def generate(self):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    self.id = secrets.token_hex(16)
    while True:
      question = f'{random.randint(1, 10)}{random.choice(["+", "-", "*", "/"])}{random.randint(1, 10)}'
      answer = str(eval(question))
      if "." not in str(answer): break
    cursor.execute("INSERT INTO math (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, answer))
    conn.commit()
    conn.close()
    return {"question": question, "answer": answer}
  def get_question(self): return f"{self.question} = ?"
  def verify(self, user_answer): 
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    if not self.id:
      conn.close()
      raise RuntimeError("Captcha not created")
      return False
    cursor.execute("SELECT answer, attempts, expires_at FROM math WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5", (self.id,))
    result = cursor.fetchone()
    if not result:
      conn.close()
      raise RuntimeError("Captcha not found or expired")
      return False
    answer, attempts, expires_at = result
    if secrets.compare_digest(str(answer), str(user_answer)):
      cursor.execute("DELETE FROM math WHERE id = ?", (self.id,))
      conn.commit()
      conn.close()
      return True
    else:
      cursor.execute("UPDATE math SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      conn.commit()
      conn.close()
      return False
  def cleanup(self):
    local_conn = sqlite3.connect(db_path)
    local_cursor = local_conn.cursor()
    local_cursor.execute("DELETE FROM math WHERE expires_at < datetime('now')")
    local_conn.commit()
    local_conn.close()
