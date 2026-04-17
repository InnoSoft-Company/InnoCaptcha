from InnoCaptcha.text import TextCaptcha

captcha = TextCaptcha()
captcha.create()
print(captcha.chars)
print(captcha.verify(input()))