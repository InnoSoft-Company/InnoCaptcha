import os, secrets, threading, wave
from scipy.signal import butter, lfilter
import numpy as np
from .utils import DB

data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/audios')

def read_wav(path):
  with wave.open(path, 'rb') as wf:
    channels = wf.getnchannels()
    sampwidth = wf.getsampwidth()
    raw = wf.readframes(wf.getnframes())
  dtype = {1: 'b', 2: '<i2', 4: '<i4'}[sampwidth]
  samples = np.frombuffer(raw, dtype=dtype).astype(np.float32)
  if channels == 2: samples = samples.reshape(-1, 2).mean(axis=1)
  samples /= float(2 ** (8 * sampwidth - 1))
  return samples

class AudioCaptcha:
  def __init__(self, lang='en'):
    self.lang = lang
    self.id     = None
    self.chars  = None
    self.audio = None
    threading.Thread(target=self.cleanup, daemon=True).start()

  def cleanup(self):
    with DB() as db:
      db.execute("DELETE FROM audio WHERE expires_at < datetime('now')")
      db.commit()

  def create(self, chars=None):
    if not chars:
      chars = [secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6)]
    self.chars = "".join(chars[0:6])
    self.id = secrets.token_hex(16)
    
    with DB() as db:
      db.execute("INSERT INTO audio (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, datetime('now', '+5 minutes'))", (self.id, self.chars))
      db.commit()
        
    silence = np.zeros(9000, dtype=np.float32)
    parts   = []
    for char in self.chars.lower():
      wav_path = os.path.join(data_dir, f"{char}.wav")     
      if not os.path.isfile(wav_path): 
        raise FileNotFoundError(f"Missing audio file for character: '{char}' at {wav_path}")
      samples = read_wav(wav_path)
      
      noise_scale = 0.005 + (secrets.randbelow(10) / 1000.0)
      noise = np.random.uniform(-noise_scale, noise_scale, len(samples)).astype(np.float32)
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
      raise RuntimeError("Captcha not created" if self.lang == 'en' else "لم يتم إنشاء الكابتشا")
        
    with DB() as db:
      db.execute("SELECT answer, attempts, expires_at FROM audio WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5", (self.id,))
      result = db.fetchone()
        
      if not result:
        return "Captcha expired or max attempts reached" if self.lang == 'en' else "انتهت صلاحية الكابتشا أو وصلت لأقصى عدد محاولات"
          
      answer, attempts, expires_at = result
      if secrets.compare_digest(user_input.lower(), answer.lower()):
        db.execute("DELETE FROM audio WHERE id = ?", (self.id,))
        db.commit()
        return True
          
      db.execute("UPDATE audio SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      db.commit()
    return False
