import sqlite3, os

# Centralized database path
DB_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

class DB:
  def __init__(self, db_path=None):
    self.db_path = db_path if db_path else DB_PATH
    self.conn = sqlite3.connect(self.db_path)
    self.cursor = self.conn.cursor()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.conn:
      self.conn.close()

  def execute(self, query, params=()):
    self.cursor.execute(query, params)

  def commit(self):
    self.conn.commit()

  def fetchone(self):
    return self.cursor.fetchone()
