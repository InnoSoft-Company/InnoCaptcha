from datetime import datetime
import os, pytz

os.chdir(os.path.dirname(os.path.abspath(__file__)))

project = "InnoCaptcha"
branch = "main"

try:
  if input("Did you have a git repo installed? (y/n): ").lower()[0] == "n":
    os.system(f'''git init && \
    git remote add origin https://github.com/InnoSoft-Company/{project}.git ''')
except: pass

q = input("Adding a commit message? (Skip avilable): ")

os.system(f'''
git add . && \
git commit -m "{datetime.now(pytz.timezone("Africa/Cairo")).strftime("%d-%m-%Y | %H:%M:%S")}{ f' | {q}' if q else '' }" && \
git branch -M main && \
git push https://github.com/InnoSoft-Company/{project}.git {branch} --force
''')

#git clone https://github.com/InnoSoft-Company/InnoCaptcha
