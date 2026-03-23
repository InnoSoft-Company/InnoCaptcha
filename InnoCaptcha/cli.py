import sys, subprocess, argparse
from . import __version__

def main():
  parser = argparse.ArgumentParser(prog="incaptcha", description="InnoCaptcha CLI — manage and upgrade your InnoCaptcha installation")
  parser.add_argument("--version", action="version", version=f"InnoCaptcha Version: {__version__}", help="Show the current version")
  parser.add_argument("--upgrade", action="store_true", help="Upgrade InnoCaptcha to the latest version")
  args = parser.parse_args()
  if args.upgrade:
    print("Upgrading InnoCaptcha...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "InnoCaptcha"])
    print("Upgrade completed!")
