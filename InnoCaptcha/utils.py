import sqlite3, os, logging, json
from datetime import datetime
from cryptography.fernet import Fernet

# Centralized paths
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH  = os.path.join(BASE_DIR, 'data/dbs/captcha.db')
LOG_DIR  = os.path.join(BASE_DIR, 'data/logs')
SECRET_KEY_PATH = os.path.join(BASE_DIR, 'data/secret.key')

# Ensure directories exist
os.makedirs(os.path.dirname(DB_PATH), mode=0o700, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Setup Logging
def setup_logging():
  log_file = os.path.join(LOG_DIR, f"innocaptcha_{datetime.now().strftime('%Y-%m-%d')}.log")
  logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def log_event(event_type, message, metadata=None):
  setup_logging()
  entry = {"event": event_type, "msg": message, "meta": metadata or {}}
  logging.info(json.dumps(entry))

def get_encryption_key():
  key = os.environ.get('INNOCAPTCHA_KEY')
  if key:
    return key.encode() if isinstance(key, str) else key
  
  if os.path.exists(SECRET_KEY_PATH):
    with open(SECRET_KEY_PATH, 'rb') as f:
      return f.read().strip()
  
  new_key = Fernet.generate_key()
  with open(SECRET_KEY_PATH, 'wb') as f:
    f.write(new_key)
  os.chmod(SECRET_KEY_PATH, 0o600)
  return new_key

ALLOWED_TABLES = {'text', 'audio', 'math', 'voice', 'image'}

class DB:
  def __init__(self, db_path=None):
    self.db_path = db_path if db_path else DB_PATH
    self.conn = None
    try:
      self.conn = sqlite3.connect(self.db_path)
      if os.path.exists(self.db_path):
        os.chmod(self.db_path, 0o600)
      self.cursor = self.conn.cursor()
      self._initialize_schema()
    except Exception as e:
      if self.conn:
        self.conn.close()
      raise e

  def _initialize_schema(self):
    """Ensure tables exist with new security columns (ip_address, session_id)."""
    for table in ALLOWED_TABLES:
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
    
    self.conn.commit()

  def __enter__(self): return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    if self.conn: self.conn.close()

  def execute(self, query, params=()): self.cursor.execute(query, params)

  def commit(self): self.conn.commit()

  def fetchone(self): return self.cursor.fetchone()

