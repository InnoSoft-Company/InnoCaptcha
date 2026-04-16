"""
Unit tests for InnoCaptcha: TextCaptcha, AudioCaptcha, MathCaptcha.

Run with:
    python -m pytest test_innocaptcha.py -v
or:
    python test_innocaptcha.py
"""

import os
import sys
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PACKAGE_DIR = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, PACKAGE_DIR)

DB_PATH = os.path.join(PACKAGE_DIR, "InnoCaptcha", "data/dbs/captcha.db")

def init_db():
    """Create all tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    tables = ['text', 'audio', 'math', 'voice', 'image']
    for table in tables:
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
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

    def test_create_sets_id(self):
        self.captcha.create()
        self.assertIsNotNone(self.captcha.id)
        self.assertEqual(len(self.captcha.id), 32)

    def test_create_sets_chars_max_6(self):
        self.captcha.create(['A', 'B', 'C', 'D', 'E', 'F', 'G'])
        self.assertEqual(len(self.captcha.chars), 6)

    def test_create_uses_provided_chars(self):
        self.captcha.create('XYZ123')
        self.assertEqual(self.captcha.chars, 'XYZ123')

    def test_create_inserts_row_in_db(self):
        self.captcha.create()
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute("SELECT id, answer FROM text WHERE id = ?", (self.captcha.id,)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], self.captcha.id)
        self.assertEqual(row[1], self.captcha.chars)

    def test_save_writes_file(self):
        self.captcha.create()
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            path = f.name
        try:
            self.captcha.save(path)
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            if os.path.exists(path): os.unlink(path)

    def test_verify_correct_answer_returns_true(self):
        self.captcha.create()
        result = self.captcha.verify(self.captcha.chars)
        self.assertTrue(result)

    def test_verify_wrong_answer_returns_false(self):
        self.captcha.create()
        result = self.captcha.verify("WRONG1")
        self.assertFalse(result)

    def test_verify_returns_message_after_5_attempts(self):
        self.captcha.create()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE text SET attempts = 5 WHERE id = ?", (self.captcha.id,))
            conn.commit()
        result = self.captcha.verify("WRONG1")
        self.assertIsInstance(result, str)

# ---------------------------------------------------------------------------
# AudioCaptcha Tests
# ---------------------------------------------------------------------------
class TestAudioCaptcha(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        try:
            from InnoCaptcha.audio import AudioCaptcha, data_dir
            cls.AudioCaptcha = AudioCaptcha
            cls.wav_available = os.path.isfile(os.path.join(data_dir, 'a.wav'))
        except ImportError:
            cls.AudioCaptcha = None
            cls.wav_available = False

    def setUp(self):
        if not self.AudioCaptcha: self.skipTest("AudioCaptcha not available")
        self.captcha = self.AudioCaptcha()

    def test_create_sets_id(self):
        if not self.wav_available: self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        self.assertIsNotNone(self.captcha.id)

    def test_verify_correct_answer_returns_true(self):
        if not self.wav_available: self.skipTest("WAV files not present")
        self.captcha.create("ABCDEF")
        result = self.captcha.verify(self.captcha.chars)
        self.assertTrue(result)

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

    def test_init_sets_question(self):
        self.assertIsNotNone(self.captcha.question)
        self.assertTrue(any(op in self.captcha.question for op in ['+', '-', '×', '*', '/']))

    def test_verify_correct_answer_returns_true(self):
        result = self.captcha.verify(self.captcha.answer)
        self.assertTrue(result)

    def test_verify_returns_message_if_expired(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE math SET expires_at = datetime('now', '-1 minute') WHERE id = ?", (self.captcha.id,))
            conn.commit()
        result = self.captcha.verify(self.captcha.answer)
        self.assertIsInstance(result, str)

if __name__ == '__main__':
    unittest.main(verbosity=2)
