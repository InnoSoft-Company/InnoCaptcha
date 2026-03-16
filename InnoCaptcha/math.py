import random, sqlite3, os, threading

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'captchas.db')

class MathCaptcha:
  def __init__(self):
    generated = self.generate()
    self.question, self.answer = generated.values()
    threading.Thread(target=self.cleanup, daemon=True).start()
  def generate(self):
    while True:
      question = f'{random.randint(1, 10)}{random.choice(["+", "-", "*", "/"])}{random.randint(1, 10)}'
      answer = eval(question)
      if "." not in str(answer): break
    return {"question": question, "answer": answer}
  def get_question(self): return f"{self.question} = ?"
  def verify(self, answer): return str(answer) == str(self.answer)
  def cleanup(self):
    local_conn = sqlite3.connect(db_path)
    local_cursor = local_conn.cursor()
    local_cursor.execute("DELETE FROM captchas WHERE expires_at < datetime('now')")
    local_conn.commit()
    local_conn.close()
