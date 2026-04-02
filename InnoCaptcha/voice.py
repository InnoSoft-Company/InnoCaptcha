import os, secrets, threading, io
import speech_recognition as sr
from pydub import AudioSegment
from pydub.effects import normalize
from . import utils

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

phrases = [
    "the quick brown fox jumps over the lazy dog",
    "pack my box with five dozen liquor jugs",
    "how vexingly quick daft zebras jump",
    "the five boxing wizards jump quickly",
    "sphinx of black quartz judge my vow",
    "two driven jocks help fax my big quiz",
    "five quacking zephyrs jolt my wax bed",
    "the jay pig fox zebra and my wolves quack",
    "blowzy red vixens fight for a quick jump",
    "glib jocks quiz nymph to vex dwarf",
]

class VoiceCaptcha():
    def __init__(self, language='en-US'):
        self.language = language
        self.id = None
        self.phrase = None
        self.recognizer = sr.Recognizer()
        threading.Thread(target=self.cleanup, daemon=True).start()

    def cleanup(self):
        db = utils.DB(db_path)
        db.execute("DELETE FROM voice WHERE expires_at < datetime('now')")
        db.commit()

    def create(self, phrase=None):
        self.id = secrets.token_hex(16)
        self.phrase = phrase if phrase else secrets.choice(phrases)
        db = utils.DB(db_path)
        db.execute("""INSERT INTO voice (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))""", (self.id, self.phrase))
        db.commit()

    def verify(self, audio_bytes):
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
        db = utils.DB(db_path)
        if not self.id:
            db.commit()
            raise RuntimeError("Captcha not created")

        db.execute(
            "SELECT answer, attempts, expires_at FROM voice "
            "WHERE id = ? AND expires_at >= datetime('now') AND attempts < 5",
            (self.id,)
        )
        result = db.fetchone()
        if not result:
            db.commit()
            raise RuntimeError("You have reached the maximum number of attempts or the captcha has expired.")

        answer, attempts, expires_at = result

        if transcript is None:
            db.execute("UPDATE voice SET attempts = attempts + 1 WHERE id = ?", (self.id,))
            db.commit()
            return False

        if secrets.compare_digest(transcript.lower(), answer.lower()):
            db.execute("DELETE FROM voice WHERE id = ?", (self.id,))
            db.commit()
            return True
        else:
            db.execute("UPDATE voice SET attempts = attempts + 1 WHERE id = ?", (self.id,))
            db.commit()
            return False