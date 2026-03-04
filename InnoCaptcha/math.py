import random

class MathCaptcha:
  def __init__(self):
    generated = self.generate()
    self.question, self.answer = generated.values()
  def generate(self):
    while True:
      question = f'{random.randint(1, 10)}{random.choice(["+", "-", "*", "/"])}{random.randint(1, 10)}'
      answer = eval(question)
      if "." not in str(answer): break
    return {"question": question, "answer": answer}
  def get_question(self): return f"{self.question} = ?"
  def verify(self, answer): return str(answer) == str(self.answer)
