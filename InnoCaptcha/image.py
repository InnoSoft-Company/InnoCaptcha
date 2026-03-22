from ultralytics import YOLO
from PIL import Image
import numpy as np
import cv2
import os
import secrets
import sqlite3
import threading
from . import utils

images_dir = os.path.join(os.path.dirname(__file__), 'data', 'images')
db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data/dbs/captcha.db')

class ImageCaptcha:
    def cleanup(self):
        db = utils.DB(db_path)
        db.execute("DELETE FROM image WHERE expires_at < datetime('now')")
        db.commit()

    def __init__(self):
        self.model = YOLO(os.path.join('InnoCaptcha', 'data', 'models', 'yolo11n.pt'))
        self.image_class = secrets.choice(os.listdir(images_dir))
        d = os.path.join(images_dir, self.image_class)
        self.image_path = os.path.join(d, secrets.choice(os.listdir(d)))
        self.annotation_coordinates = []
        self.image = None
        self.id = None
        threading.Thread(target=self.cleanup, daemon=True).start()

    def create(self):
        self.id = secrets.token_hex(16)
        db = utils.DB(db_path)
        pil_img = Image.open(self.image_path).convert('RGB')
        img = np.array(pil_img)
        results = self.model(img)
        for result in results:
            for box in result.boxes.xyxy.cpu().numpy():
                x1, y1, x2, y2 = map(int, box)
                self.annotation_coordinates.append((x1, y1, x2, y2))
        h, w = img.shape[:2]
        for i in range(1, 3):
            cv2.line(img, (i * w // 3, 0), (i * w // 3, h), (255, 0, 0), 2)
            cv2.line(img, (0, i * h // 3), (w, i * h // 3), (255, 0, 0), 2)
        h, w = img.shape[:2]
        grid_mapping = {
            1: (0, 0, w // 3, h // 3),
            2: (w // 3, 0, 2 * w // 3, h // 3),
            3: (2 * w // 3, 0, w, h // 3),
            4: (0, h // 3, w // 3, 2 * h // 3),
            5: (w // 3, h // 3, 2 * w // 3, 2 * h // 3),
            6: (2 * w // 3, h // 3, w, 2 * h // 3),
            7: (0, 2 * h // 3, w // 3, h),
            8: (w // 3, 2 * h // 3, 2 * w // 3, h),
            9: (2 * w // 3, 2 * h // 3, w, h)
        }
        correct_grids = set()
        for (x1, y1, x2, y2) in self.annotation_coordinates:
            for grid_num, (gx1, gy1, gx2, gy2) in grid_mapping.items():
                if not (x2 < gx1 or x1 > gx2 or y2 < gy1 or y1 > gy2):
                    correct_grids.add(grid_num)
        db.execute("INSERT INTO image (id, answer, attempts, created_at, expires_at) VALUES (?, ?, 0, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", (self.id, ",".join(map(str, correct_grids))))
        db.commit()
        self.image = img

    def verify(self):
        db = utils.DB(db_path)
        db.execute("SELECT answer, attempts FROM image WHERE id = ? AND expires_at > datetime('now') AND attempts < 5", (self.id,))
        result = db.fetchone()
        if not result:
            return False
        Image.fromarray(self.image).show()
        user_input = input("Choose the grids that containing the object (1-9 comma-separated)")
        correct_answer = result[0]
        if user_input == correct_answer:
            db.execute("DELETE FROM image WHERE id = ?", (self.id,))
            db.commit()
            return True
        else:
            db.execute("UPDATE image SET attempts = attempts + 1 WHERE id = ?", (self.id,))
            db.commit()
            return False
    def save(self, path=None):
        if self.image is None or self.id is None:
            raise ValueError("No captcha created.")
            return False
        if not path:
            Image.fromarray(self.image).save("captcha.png")
        else:
            Image.fromarray(self.image).save(path)