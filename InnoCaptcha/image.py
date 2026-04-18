import cv2, threading, os, secrets
from ultralytics import YOLO
from PIL import Image
import numpy as np
from .utils import DB, log_event
from cryptography.fernet import Fernet

images_dir = os.path.join(os.path.dirname(__file__), 'data', 'images')

class ImageCaptcha:
  def cleanup(self):
    with DB() as db:
      db.execute("DELETE FROM image WHERE expires_at < datetime('now')")
      db.commit()

  def __init__(self, lang='en'):
    self.lang = lang
    self.model = YOLO(os.path.join('InnoCaptcha', 'data', 'models', 'yolo11n.pt'))
    classes = sorted(os.listdir(images_dir))
    if not classes:
      raise FileNotFoundError("No image classes found in data/images")
            
    self.image_class = secrets.choice(classes)
    d = os.path.join(images_dir, self.image_class)
    self.image_path = os.path.join(d, secrets.choice(sorted(os.listdir(d))))
    self.annotation_coordinates = []
    self.image = None
    self.id = None
    threading.Thread(target=self.cleanup, daemon=True).start()

  def create(self, ip=None, session_id=None):
    self.id = secrets.token_hex(16)
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
    answer = ",".join(map(str, sorted(correct_grids)))
    with DB() as db:
      db.execute("SELECT value FROM encryption_key limit 1")
      key = db.fetchone()
      if key:
        fernet = Fernet(key[0])
        answer = fernet.encrypt(answer.encode())
      db.execute("INSERT INTO image (id, answer, attempts, ip_address, session_id, created_at, expires_at) VALUES (?, ?, 0, ?, ?, CURRENT_TIMESTAMP, (datetime('now', '+5 minutes')))", 
                 (self.id, answer, ip, session_id))
      db.commit()
    
    log_event("CAPTCHA_CREATED", f"Image captcha created: {self.id}", {"module": "image", "ip": ip, "session": session_id})
    self.image = img
    return self.id

  def verify(self, user_input, ip=None, session_id=None):
    if not self.id:
      raise RuntimeError("Captcha not created" if self.lang == 'en' else "لم يتم إنشاء الكابتشا")
            
    with DB() as db:
      db.execute("SELECT answer, attempts, expires_at, ip_address, session_id FROM image WHERE id = ?", (self.id,))
      result = db.fetchone()
      if not result:
        log_event("VERIFY_ABORT", f"Captcha not found: {self.id}", {"module": "image", "ip": ip})
        return "Captcha not found" if self.lang == 'en' else "الكابتشا غير موجودة"
      
      answer, attempts, expires_at, db_ip, db_session = result

      db.execute("SELECT value FROM encryption_key limit 1")
      key = db.fetchone()
      if key:
        fernet = Fernet(key[0])
        
        answer = fernet.decrypt(answer).decode()
      # Context Binding Validation (#5)
      print(f"Answer from DB: {answer}, User Input: {user_input}, DB IP: {db_ip}, User IP: {ip}, DB Session: {db_session}, User Session: {session_id}")  # Debug statement
      if (db_ip and ip and db_ip != ip) or (db_session and session_id and db_session != session_id):
        log_event("VERIFY_REJECTED", f"Context mismatch for {self.id}", {"module": "image", "ip": ip, "db_ip": db_ip})
        return "Security context mismatch" if self.lang == 'en' else "خطأ في التحقق من المصدر"

      # Rate Limiting & Expiry (#4)
      if attempts >= 5:
        log_event("VERIFY_REJECTED", f"Max attempts reached: {self.id}", {"module": "image", "ip": ip})
        return "Max attempts reached" if self.lang == 'en' else "تجاوزت عدد المحاولات"
      
      db.execute("SELECT 1 FROM image WHERE id = ? AND expires_at >= datetime('now')", (self.id,))
      if not db.fetchone():
        log_event("VERIFY_REJECTED", f"Captcha expired: {self.id}", {"module": "image", "ip": ip})
        return "Captcha expired" if self.lang == 'en' else "انتهت صلاحية الكابتشا"

      if user_input == answer:
        db.execute("DELETE FROM image WHERE id = ?", (self.id,))
        db.commit()
        log_event("VERIFY_SUCCESS", f"Captcha verified: {self.id}", {"module": "image", "ip": ip})
        return True
            
      db.execute("UPDATE image SET attempts = attempts + 1 WHERE id = ?", (self.id,))
      db.commit()
      log_event("VERIFY_FAILED", f"Wrong answer for {self.id}", {"module": "image", "ip": ip, "attempt": attempts+1})
      return False

  def save(self, path=None):
    if self.image is None or self.id is None:
      raise ValueError("No captcha created.")
            
    final_image = Image.fromarray(self.image)
    if not path:
      path = "captcha_image.png"
    final_image.save(path)
