import os, secrets, sqlite3, threading, wave
import numpy as np
from scipy.signal import butter, lfilter

data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
db_path  = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'captchas.db')

def read_wav(path):
  with wave.open(path, 'rb') as wf:
    channels = wf.getnchannels()
    sampwidth = wf.getsampwidth()
    raw = wf.readframes(wf.getnframes())

  dtype = {1: 'b', 2: '<i2', 4: '<i4'}[sampwidth]
  samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)

  if channels == 2:
    samples = samples.reshape(-1, 2).mean(axis=1)

  samples /= float(2 ** (8 * sampwidth - 1))
  return samples


class AudioCaptcha:
  def __init__(self):
    self.id     = None
    self.chars  = None
    self.audio = None

    threading.Thread(target=self.cleanup, daemon=True).start()

  def cleanup(self):
    local_conn = sqlite3.connect(db_path)
    local_cursor = local_conn.cursor()
    local_cursor.execute("DELETE FROM captchas WHERE expires_at < datetime('now')")
    local_conn.commit()
    local_conn.close()

  def create(self, chars):
    self.chars = "".join(chars[0:6])
    self.id = secrets.token_hex(16)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO captchas (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, datetime('now', '+5 minutes'))""", (self.id, self.chars))
    conn.commit()
    conn.close()
    
    silence = np.zeros(9000, dtype=np.float32)
    parts   = []
    
    for char in chars.lower():
      wav_path = os.path.join(data_dir, f"{char}.wav")
      
      if not os.path.isfile(wav_path):
        raise FileNotFoundError(f"Missing audio file for character: '{char}' at {wav_path}")
      
      samples = read_wav(wav_path)
      
      noise = np.random.uniform(-0.01, 0.01, len(samples)).astype(np.float32)
      char_audio = samples + noise
      
      factor  = 0.5 + (secrets.randbits(8) / 255 - 0.5) * 0.05
      new_len = max(1, int(len(samples) / factor))
      indices = np.linspace(0, len(samples) - 1, new_len).astype(np.int32)
      char_audio = char_audio[indices]
      
      parts.append(char_audio)
      parts.append(silence.copy())
      
    combined = np.concatenate(parts).astype(np.float32)
    
    combined = combined * (0.5 + secrets.randbits(8) / 255 * 0.2)
    
    b, a = butter(2, 3400 / (44100 / 2), btype='low')
    combined = lfilter(b, a, combined)
    
    self.audio = combined

  def save(self, path):
    if self.audio is None:
      raise ValueError("No captcha created.")
        
    samples = np.clip(self.audio, -1.0, 1.0)
    pcm = (samples * 32767).astype(np.int16)
    
    with wave.open(path, 'wb') as wf:
      wf.setnchannels(1)
      wf.setsampwidth(2)
      wf.setframerate(44100)
      wf.writeframes(pcm.tobytes())

  def verify(self, user_input):
    if not self.id:
      raise RuntimeError("Captcha not created")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""SELECT answer, attempts, expires_at FROM captchas WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5""",(self.id,))
    result = cursor.fetchone()

    if not result:
      conn.close()
      return "You have reached the maximum number of attempts or the captcha has expired."

    answer, attempts, expires_at = result

    if secrets.compare_digest(user_input.lower(), answer.lower()):
      cursor.execute("DELETE FROM captchas WHERE id = ?", (self.id,))
      conn.commit()
      conn.close()
      return True
    else:
      cursor.execute("UPDATE captchas SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      conn.commit()
      conn.close()
      return False