import subprocess, os, pytz, sys
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

PROJECT, REMOTE_NAME = "InnoCaptcha", "origin"
REMOTE_URL = f"https://github.com/InnoSoft-Company/{PROJECT}.git"

def run(cmd):
  if subprocess.run(cmd, shell=True).returncode != 0: sys.exit(1) 

def repo_exists(): return os.path.isdir(".git")

def remote_exists():
  try:
    subprocess.check_output("git remote", shell=True)
    return REMOTE_NAME in subprocess.check_output("git remote", shell=True).decode()
  except: return False

def get_current_branch(): return subprocess.check_output("git branch --show-current", shell=True).decode().strip() or "main"

if not repo_exists(): run("git init")
if not remote_exists(): run(f"git remote add {REMOTE_NAME} {REMOTE_URL}")

if not bool(subprocess.check_output("git status --porcelain", shell=True).decode().strip()):
  print("No changes to commit.")
  sys.exit(0)
commit = input("Commit message (optional): ").strip()
run("git add .")
run(f'git commit -m "{datetime.now(pytz.timezone("Africa/Cairo")).strftime("%d-%m-%Y | %H:%M:%S")}{f" | {commit}" if commit else ""}"')
branch = get_current_branch()
run(f"git pull {REMOTE_NAME} {branch}")
run(f"git push {REMOTE_NAME} {branch}")

#git clone https://github.com/InnoSoft-Company/InnoCaptcha
