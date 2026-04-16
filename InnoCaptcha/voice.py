import os, secrets, threading, io, speech_recognition as sr
from pydub import AudioSegment
from pydub.effects import normalize
from . import utils

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

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
        threading.Thread(target=self.cleanup, daemon=True).start()

    def cleanup(self):
        with utils.DB(db_path) as db:
            db.execute("DELETE FROM voice WHERE expires_at < datetime('now')")
            db.commit()

    def create(self, phrase=None):
        self.id = secrets.token_hex(16)
        if not phrase:
            phrases = phrases_ar if self.lang_code == 'ar' else phrases_en
            self.phrase = secrets.choice(phrases)
        else:
            self.phrase = phrase
            
        with utils.DB(db_path) as db:
            db.execute("""INSERT INTO voice (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))""", (self.id, self.phrase))
            db.commit()

    def verify(self, audio_bytes):
        if not audio_bytes:
            return False
            
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_bytes))
            audio = normalize(audio)
            with io.BytesIO() as wav_io:
                audio.export(wav_io, format="wav")
                wav_io.seek(0)
                with sr.AudioFile(wav_io) as source:
                    audio_data = self.recognizer.record(source)
                    try:
                        transcript = self.recognizer.recognize_google(audio_data, language=self.language)
                    except sr.UnknownValueError:
                        transcript = None
        except Exception:
            transcript = None

        if not self.id:
            raise RuntimeError("Captcha not created" if self.lang_code == 'en' else "لم يتم إنشاء الكابتشا")

        with utils.DB(db_path) as db:
            db.execute(
                "SELECT answer, attempts, expires_at FROM voice "
                "WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5",
                (self.id,)
            )
            result = db.fetchone()
            if not result:
                return "Captcha expired or max attempts reached" if self.lang_code == 'en' else "انتهت صلاحية الكابتشا أو وصلت لأقصى عدد محاولات"

            answer, attempts, expires_at = result

            if transcript is None:
                db.execute("UPDATE voice SET attempts = attempts + 1 WHERE id = ?", (self.id,))
                db.commit()
                return False

            if secrets.compare_digest(transcript.lower().strip(), answer.lower().strip()):
                db.execute("DELETE FROM voice WHERE id = ?", (self.id,))
                db.commit()
                return True
            
            db.execute("UPDATE voice SET attempts = attempts + 1 WHERE id = ?", (self.id,))
            db.commit()
        return False
