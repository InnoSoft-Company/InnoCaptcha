from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha()
captcha.create()
print(captcha.chars)
captcha.image.show()
print(captcha.verify(input()))