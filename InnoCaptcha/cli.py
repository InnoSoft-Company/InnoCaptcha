from . import __version__
import sys

def main():
  if "--version" in sys.argv: print(f"InnoCaptcha Version: {__version__}") 
