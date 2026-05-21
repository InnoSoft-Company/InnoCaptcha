import os, secrets, threading, io, speech_recognition as sr
from pydub.effects import normalize
from .utils import DB, log_event, get_encryption_key
from pydub import AudioSegment
from cryptography.fernet import Fernet

phrases_en = [
  "the quick brown fox jumps over the lazy dog",
  "pack my box with five dozen liquor jugs",
  "how vexingly quick daft zebras jump",
  "the five boxing wizards jump quickly",
  "sphinx of black quartz judge my vow",
  "two driven jocks help fax my big quiz",
]

phrases_ar = [
  "ذهب الطالب إلى المدرسة مبكرا",
  "السماء صافية والجو جميل اليوم",
  "أكل الولد التفاحة الحمراء اللذيذة",
  "القراءة تغذي العقل والروح دائما",
  "العلم نور والجهل ظلام دامس",
]

class VoiceCaptcha():
  def __init__(self, language='en-US'):
    self.language = language
    self.lang_code = 'ar' if language.startswith('ar') else 'en'
    self.id = None
    self.phrase = None
    self.recognizer = sr.Recognizer()
    
  def cleanup(self):
    with DB() as db:
      db.execute("DELETE FROM voice WHERE expires_at < datetime('now')")
      db.commit()
  
  def create(self, phrase=None, ip=None, session_id=None):
    self.cleanup()
    self.id = secrets.token_hex(16)
    if not phrase:
      phrases = phrases_ar if self.lang_code == 'ar' else phrases_en
      self.phrase = secrets.choice(phrases)
    else: self.phrase = phrase    
    with DB() as db:
      key = get_encryption_key()
      fernet = Fernet(key)
      encrypted_phrase = fernet.encrypt(self.phrase.encode())

      db.execute("""INSERT INTO voice (id, answer, attempts, ip_address, session_id, created_at, expires_at) VALUES (?, ?, 0, ?, ?, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))""", (self.id, encrypted_phrase, ip, session_id))
      db.commit()
    log_event("CAPTCHA_CREATED", f"Voice captcha created: {self.id}", {"module": "voice", "ip": ip, "session": session_id})
    return self.id

  def verify(self, audio_bytes, ip=None, session_id=None):
    if not self.id:
      raise RuntimeError("Captcha not created" if self.lang_code == 'en' else "لم يتم إنشاء الكابتشا")
    with DB() as db:
      db.execute("SELECT answer, attempts, expires_at, ip_address, session_id FROM voice WHERE id = ?", (self.id,))
      result = db.fetchone()
      if not result:
        log_event("VERIFY_ABORT", f"Captcha not found: {self.id}", {"module": "voice", "ip": ip})
        return "Captcha not found" if self.lang_code == 'en' else "الكابتشا غير موجودة"
      answer, attempts, expires_at, db_ip, db_session = result
      # Encrypting user input for secure comparison
      key = get_encryption_key()
      fernet = Fernet(key)
      try:
        answer = fernet.decrypt(answer).decode()
      except Exception:
        log_event("DECRYPT_ERROR", f"Failed to decrypt answer for {self.id}", {"module": "voice"})
        return "Captcha verification error" if self.lang_code == 'en' else "خطأ في التحقق"
      # Context Binding Validation (#5)
      ip_match = not db_ip or secrets.compare_digest(db_ip, ip or "")
      session_match = not db_session or secrets.compare_digest(db_session, session_id or "")
      if not ip_match or not session_match:
        log_event("VERIFY_REJECTED", f"Context mismatch for {self.id}", {"module": "voice", "ip": ip, "db_ip": db_ip})
        return "Security context mismatch" if self.lang_code == 'en' else "خطأ في التحقق من المصدر"
      if attempts >= 5:
        log_event("VERIFY_REJECTED", f"Max attempts reached: {self.id}", {"module": "voice", "ip": ip})
        return "Max attempts reached" if self.lang_code == 'en' else "تجاوزت عدد المحاولات"
      db.execute("SELECT 1 FROM voice WHERE id = ? AND expires_at >= datetime('now')", (self.id,))
      if not db.fetchone():
        log_event("VERIFY_REJECTED", f"Captcha expired: {self.id}", {"module": "voice", "ip": ip})
        return "Captcha expired" if self.lang_code == 'en' else "انتهت صلاحية الكابتشا"
      transcript = None
      if audio_bytes:
        if len(audio_bytes) > 10 * 1024 * 1024: # 10 MB limit
          log_event("VERIFY_REJECTED", f"Audio file too large", {"module": "voice", "ip": ip})
          return "Audio file too large. Max 10MB."
        try:
          audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
          audio = normalize(audio)
          with io.BytesIO() as wav_io:
            audio.export(wav_io, format="wav")
            wav_io.seek(0)
            with sr.AudioFile(wav_io) as source:
              audio_data = self.recognizer.record(source)
              transcript = self.recognizer.recognize_google(audio_data, language=self.language)
        except sr.UnknownValueError:
          return "Could not understand audio. Please try again."
        except sr.RequestError as e:
          log_event("STT_ERROR", f"Google STT failed: {e}", {"module": "voice"})
          return "Speech service unavailable. Please try again."
        except Exception as e:
          log_event("STT_ERROR", f"Unexpected STT error: {e}", {"module": "voice"})
          return "Verification error."
      if transcript and secrets.compare_digest(transcript.lower().strip(), answer.lower().strip()):
        db.execute("DELETE FROM voice WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_SUCCESS", f"Captcha verified: {self.id}", {"module": "voice", "ip": ip})
        return True
      db.execute("UPDATE voice SET attempts = attempts + 1 WHERE id = ? AND attempts < 5", (self.id,))
      db.commit()
      log_event("VERIFY_FAILED", f"Wrong answer for {self.id}", {"module": "voice", "ip": ip, "attempt": attempts+1})
    return False
