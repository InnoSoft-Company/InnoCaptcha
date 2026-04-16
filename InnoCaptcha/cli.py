import sys, subprocess, argparse, os
from . import __version__
from .utils import LOG_DIR

def main():
  parser = argparse.ArgumentParser(prog="InnoCaptcha", description="InnoCaptcha CLI — manage and monitor your InnoCaptcha installation")
  parser.add_argument("--version", action="version", version=f"InnoCaptcha Version: {__version__}", help="Show the current version")
  parser.add_argument("--upgrade", action="store_true", help="Upgrade InnoCaptcha to the latest version")
  parser.add_argument("--logs", action="store_true", help="View the latest security and operational logs")
  parser.add_argument("--tail", type=int, default=20, help="Number of log lines to show (default: 20)")
  
  args = parser.parse_args()
  
  if args.upgrade:
    print("Upgrading InnoCaptcha...")
    try:
      subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "InnoCaptcha"])
      print("Upgrade completed!")
    except Exception as e:
      print(f"Upgrade failed: {e}")
      sys.exit(1)

  if args.logs:
    if not os.path.exists(LOG_DIR):
      print("No logs found.")
      return
    
    log_files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")], reverse=True)
    if not log_files:
      print("No log files found.")
      return
    
    latest_log = os.path.join(LOG_DIR, log_files[0])
    print(f"--- Showing latest {args.tail} lines from {log_files[0]} ---")
    try:
      with open(latest_log, 'r') as f:
        lines = f.readlines()
        for line in lines[-args.tail:]:
          print(line.strip())
    except Exception as e:
      print(f"Error reading logs: {e}")

if __name__ == "__main__":
  main()
