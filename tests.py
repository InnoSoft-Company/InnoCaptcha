"""
Unit tests for InnoCaptcha: TextCaptcha, AudioCaptcha, MathCaptcha.

Run with:
    python -m pytest test_innocaptcha.py -v
or:
    python test_innocaptcha.py

Assumptions:
- All three modules (text.py, audio.py, math.py) are importable from the same package.
- captcha.db is created/initialized before tests run (handled in setUpClass).
- Audio .wav files are present in InnoCaptcha/data/ for AudioCaptcha.create() to work.
- AudioCaptcha.create() tests that require wav files are skipped if files are missing.
"""

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Path setup — adjust if your package structure differs
# ---------------------------------------------------------------------------
PACKAGE_DIR = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, PACKAGE_DIR)

DB_PATH = os.path.join(PACKAGE_DIR, "InnoCaptcha", "data/dbs/captcha.db")

def init_db():
    """Create all three tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS text (
            id         TEXT PRIMARY KEY,
            answer     TEXT,
            attempts INTEGER DEFAULT 0 CHECK(attempts <= 5),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS audio (
            id         TEXT PRIMARY KEY,
            answer     TEXT,
            attempts INTEGER DEFAULT 0 CHECK(attempts <= 5),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS math (
            id         TEXT PRIMARY KEY,
            answer     TEXT,
            attempts INTEGER DEFAULT 0 CHECK(attempts <= 5),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME
        )
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# TextCaptcha Tests
# ---------------------------------------------------------------------------
class TestTextCaptcha(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        from InnoCaptcha.text import TextCaptcha
        cls.TextCaptcha = TextCaptcha

    def setUp(self):
        self.captcha = self.TextCaptcha()

    # --- create() ---

    def test_create_sets_id(self):
        self.captcha.create()
        self.assertIsNotNone(self.captcha.id)
        self.assertEqual(len(self.captcha.id), 32)  # token_hex(16)

    def test_create_sets_chars_max_6(self):
        self.captcha.create(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
        self.assertEqual(len(self.captcha.chars), 6)

    def test_create_uses_provided_chars(self):
        self.captcha.create('XYZ123')
        self.assertEqual(self.captcha.chars, 'XYZ123')

    def test_create_auto_generates_chars_when_none(self):
        self.captcha.create()
        self.assertEqual(len(self.captcha.chars), 6)

    def test_create_inserts_row_in_db(self):
        self.captcha.create()
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id, answer FROM text WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], self.captcha.id)
        self.assertEqual(row[1], self.captcha.chars)

    def test_create_sets_image(self):
        self.captcha.create()
        self.assertIsNotNone(self.captcha.image)

    # --- save() ---

    def test_save_writes_file(self):
        self.captcha.create()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            path = f.name
        try:
            self.captcha.save(path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    def test_save_raises_if_no_captcha(self):
        with self.assertRaises(ValueError):
            self.captcha.save("/tmp/should_not_exist.png")

    # --- verify() ---

    def test_verify_correct_answer_returns_true(self):
        self.captcha.create()
        answer = self.captcha.chars
        result = self.captcha.verify(answer)
        self.assertTrue(result)

    def test_verify_wrong_answer_returns_false(self):
        self.captcha.create()
        result = self.captcha.verify("WRONG1")
        self.assertFalse(result)

    def test_verify_correct_deletes_row(self):
        self.captcha.create()
        captcha_id = self.captcha.id
        self.captcha.verify(self.captcha.chars)
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM text WHERE id = ?", (captcha_id,)).fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_verify_increments_attempts_on_failure(self):
        self.captcha.create()
        self.captcha.verify("WRONG1")
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT attempts FROM text WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_verify_raises_if_no_id(self):
        with self.assertRaises(RuntimeError):
            self.captcha.verify("anything")

    def test_verify_returns_message_after_5_attempts(self):
        self.captcha.create()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE text SET attempts = 5 WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        result = self.captcha.verify("WRONG1")
        self.assertIsInstance(result, str)

    def test_verify_returns_message_on_expired(self):
        self.captcha.create()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE text SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        result = self.captcha.verify(self.captcha.chars)
        self.assertIsInstance(result, str)

    # --- cleanup() ---

    def test_cleanup_removes_expired_rows(self):
        self.captcha.create()
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE text SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        self.captcha.cleanup()
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM text WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNone(row)


# ---------------------------------------------------------------------------
# AudioCaptcha Tests
# ---------------------------------------------------------------------------
class TestAudioCaptcha(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        from InnoCaptcha.audio import AudioCaptcha
        cls.AudioCaptcha = AudioCaptcha

        # Detect if wav files exist
        from InnoCaptcha.audio import data_dir
        cls.data_dir = data_dir
        cls.wav_available = os.path.isfile(os.path.join(data_dir, 'a.wav'))

    def setUp(self):
        self.captcha = self.AudioCaptcha()

    # --- create() ---

    def test_create_sets_id(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        self.assertIsNotNone(self.captcha.id)
        self.assertEqual(len(self.captcha.id), 32)

    def test_create_sets_chars_max_6(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEFGH")
        self.assertEqual(len(self.captcha.chars), 6)

    def test_create_inserts_row_in_db(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id, answer FROM audio WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], self.captcha.chars)

    def test_create_raises_for_missing_wav(self):
        with self.assertRaises(FileNotFoundError):
            self.captcha.create("!@#$%^")

    def test_create_sets_audio_array(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        self.assertIsNotNone(self.captcha.audio)

    # --- save() ---

    def test_save_raises_if_no_captcha(self):
        with self.assertRaises(ValueError):
            self.captcha.save("/tmp/should_not_exist.wav")

    def test_save_writes_wav_file(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            path = f.name
        try:
            self.captcha.save(path)
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            os.unlink(path)

    # --- verify() ---

    def test_verify_raises_if_no_id(self):
        with self.assertRaises(RuntimeError):
            self.captcha.verify("anything")

    def test_verify_correct_answer_returns_true(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        result = self.captcha.verify(self.captcha.chars)
        self.assertTrue(result)

    def test_verify_wrong_answer_returns_false(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        result = self.captcha.verify("WRONG1")
        self.assertFalse(result)

    def test_verify_correct_deletes_row(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        captcha_id = self.captcha.id
        self.captcha.verify(self.captcha.chars)
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM audio WHERE id = ?", (captcha_id,)).fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_verify_increments_attempts_on_failure(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        self.captcha.verify("WRONG1")
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT attempts FROM audio WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_verify_case_insensitive(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        result = self.captcha.verify(self.captcha.chars.lower())
        self.assertTrue(result)

    def test_verify_returns_message_after_5_attempts(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE audio SET attempts = 5 WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        result = self.captcha.verify("WRONG1")
        self.assertIsInstance(result, str)

    def test_verify_returns_message_on_expired(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE audio SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        result = self.captcha.verify(self.captcha.chars)
        self.assertIsInstance(result, str)

    # --- cleanup() ---

    def test_cleanup_removes_expired_rows(self):
        if not self.wav_available:
            self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE audio SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        self.captcha.cleanup()
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM audio WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNone(row)


# ---------------------------------------------------------------------------
# MathCaptcha Tests
# ---------------------------------------------------------------------------
class TestMathCaptcha(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        from InnoCaptcha.math import MathCaptcha
        cls.MathCaptcha = MathCaptcha

    def setUp(self):
        self.captcha = self.MathCaptcha()

    # --- __init__ / generate() ---

    def test_init_sets_id(self):
        self.assertIsNotNone(self.captcha.id)
        self.assertEqual(len(self.captcha.id), 32)

    def test_init_sets_question(self):
        self.assertIsNotNone(self.captcha.question)
        # Question format: "N op N"
        self.assertTrue(any(op in self.captcha.question for op in ['+', '-', '*', '/']))

    def test_init_sets_answer(self):
        self.assertIsNotNone(self.captcha.answer)

    def test_answer_is_integer_string(self):
        # answer must not contain decimal point (enforced by generate loop)
        self.assertNotIn('.', self.captcha.answer)

    def test_generate_inserts_row_in_db(self):
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id, answer FROM math WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[1], self.captcha.answer)

    def test_get_question_format(self):
        q = self.captcha.get_question()
        self.assertTrue(q.endswith("= ?"))

    # --- verify() ---

    def test_verify_correct_answer_returns_true(self):
        result = self.captcha.verify(self.captcha.answer)
        self.assertTrue(result)

    def test_verify_wrong_answer_returns_false(self):
        result = self.captcha.verify("99999")
        self.assertFalse(result)

    def test_verify_correct_deletes_row(self):
        captcha_id = self.captcha.id
        self.captcha.verify(self.captcha.answer)
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM math WHERE id = ?", (captcha_id,)).fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_verify_increments_attempts_on_failure(self):
        self.captcha.verify("99999")
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT attempts FROM math WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertEqual(row[0], 1)

    def test_verify_raises_if_no_id(self):
        self.captcha.id = None
        with self.assertRaises(RuntimeError):
            self.captcha.verify("1")

    def test_verify_raises_if_expired(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE math SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        with self.assertRaises(RuntimeError):
            self.captcha.verify(self.captcha.answer)

    def test_verify_raises_after_5_attempts(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE math SET attempts = 5 WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        with self.assertRaises(RuntimeError):
            self.captcha.verify("99999")

    def test_verify_accepts_string_and_int(self):
        """verify() wraps both sides in str() so int input must also work."""
        result = self.captcha.verify(int(self.captcha.answer))
        self.assertTrue(result)

    # --- cleanup() ---

    def test_cleanup_removes_expired_rows(self):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("UPDATE math SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
        conn.commit()
        conn.close()
        self.captcha.cleanup()
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT id FROM math WHERE id = ?", (self.captcha.id,)).fetchone()
        conn.close()
        self.assertIsNone(row)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main(verbosity=2)