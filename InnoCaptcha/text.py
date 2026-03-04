from PIL.ImageFilter import SMOOTH
from PIL import Image, ImageFont
from PIL.Image import Resampling
from PIL.ImageDraw import Draw
import os, random, secrets

default_font = ImageFont.truetype(os.path.join(os.path.join(os.path.abspath(os.path.dirname(__file__))), 'DroidSansMono.ttf'), 40)

class TextCaptcha():
    def __init__(self, chars=None, color=(0, 0, 0), background=(255, 255, 255), width=300, height=80):
        self.image_width = width
        self.image_height = height
        self.background = background
        self.text_color = color
        self.image = Image.new('RGB', (self.image_width, self.image_height), self.background)
        self.draw = Draw(self.image)
        self.chars = chars  
        self.char_images = []
    def create(self, chars):
        for char in chars:
            temp_image = Image.new('RGBA', (1, 1))
            temp_draw = Draw(temp_image)
            left, top, w, h = temp_draw.multiline_textbbox((1, 1), char, font=default_font)          
            im = Image.new('RGBA', (int(w), int(h)))
            Draw(im).text((0, 0), char, font=default_font, fill=self.text_color)       
            im = im.crop(im.getbbox())
            angle = -45 + (secrets.randbits(32) / 64) * 90
            im = im.rotate(angle, Resampling.BILINEAR, expand=True)
            self.char_images.append(im)
        for dot in range(30):
            x1 = secrets.randbelow(self.image_width)
            y1 = secrets.randbelow(self.image_height)
            self.draw.line(((x1, y1), (x1 - 1, y1 - 1)), width=3, fill=self.text_color)
        for curve in range(10):
            x1 = secrets.randbelow(self.image_width)
            y1 = secrets.randbelow(self.image_height)
            x2 = secrets.randbelow(self.image_width)
            y2 = secrets.randbelow(self.image_height)
            start = secrets.randbelow(360)
            end = start + secrets.randbelow(360 - start)        
            x0 = min(x1, x2)
            y0 = min(y1, y2)
            x1 = max(x1, x2)
            y1 = max(y1, y2)
            self.draw.arc(((x0, y0), (x1, y1)), start, end, fill=self.text_color, width=3)
        for im in self.char_images:
            self.image.paste(im, (0, (self.image_height - im.size[1]) // 2), im)
            0 += im.size[0] + int(self.image_width * 0.05)
        self.image = self.image.filter(SMOOTH)
        self.chars = chars
    def save(self, path): self.image.save(path)
    def verify(self, user_input): return user_input == self.chars
