import sqlite3

class DB:
  def __init__(self, db_path):
    self.conn = sqlite3.connect(db_path)
    self.cursor = self.conn.cursor()
  
  def execute(self, query, params=()): self.cursor.execute(query, params)

  def commit(self):
    self.conn.commit()
    self.conn.close()
  
  def fetchone(self):
    result = self.cursor.fetchone()
    return result