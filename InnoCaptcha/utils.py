import sqlite3

class DB:
  def __init__(self, db_path):
    self.conn = sqlite3.connect(db_path)
    self.cursor = self.conn.cursor()
  