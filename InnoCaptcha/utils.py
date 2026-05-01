import sqlite3, os, logging, json
from datetime import datetime
from cryptography.fernet import Fernet

# Centralized paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data/dbs/captcha.db')
LOG_DIR  = os.path.join(BASE_DIR, 'data/logs')

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Setup Logging
def setup_logging():
  log_file = os.path.join(LOG_DIR, f"innocaptcha_{datetime.now().strftime('%Y-%m-%d')}.log")
  logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def log_event(event_type, message, metadata=None):
  setup_logging()
  entry = {"event": event_type, "msg": message, "meta": metadata or {}}
  logging.info(json.dumps(entry))

class DB:
  def __init__(self, db_path=None):
    self.db_path = db_path if db_path else DB_PATH
    self.conn = sqlite3.connect(self.db_path)
    self.cursor = self.conn.cursor()
    self._initialize_schema()

  def _initialize_schema(self):
    """Ensure tables exist with new security columns (ip_address, session_id)."""
    tables = ['text', 'audio', 'math', 'voice', 'image']
    for table in tables:
      self.cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table} (
          id         TEXT PRIMARY KEY,
          answer     TEXT,
          attempts   INTEGER DEFAULT 0 CHECK(attempts <= 5),
          ip_address TEXT,
          session_id TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          expires_at DATETIME
        )
      """)
      self.cursor.execute(f"PRAGMA table_info({table})")
      columns = [row[1].lower() for row in self.cursor.fetchall()]
      if 'ip_address' not in columns:
        try: self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN ip_address TEXT")
        except sqlite3.OperationalError: pass
      if 'session_id' not in columns:
        try: self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN session_id TEXT")
        except sqlite3.OperationalError: pass
    
    # Encryption key table
    self.cursor.execute("""CREATE TABLE IF NOT EXISTS encryption_key (value TEXT)""")
    self.cursor.execute("SELECT COUNT(*) FROM encryption_key")
    if self.cursor.fetchone()[0] == 0:
      key = Fernet.generate_key()
      self.cursor.execute("INSERT INTO encryption_key (value) VALUES (?)", (key,))
    self.conn.commit()
  def __enter__(self): return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.conn: self.conn.close()

  def execute(self, query, params=()): self.cursor.execute(query, params)

  def commit(self): self.conn.commit()

  def fetchone(self): return self.cursor.fetchone()
