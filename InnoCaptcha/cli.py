import sys, subprocess, argparse, os
from . import __version__
from .utils import LOG_DIR
from .text import TextCaptcha
from .audio import AudioCaptcha
from .math import MathCaptcha
from .voice import VoiceCaptcha
from .image import ImageCaptcha

def main():
    parser = argparse.ArgumentParser(
        prog="InnoCaptcha", 
        description="InnoCaptcha CLI \u2014 professional, multi-modal CAPTCHA management from your terminal.",
        epilog="For more information, visit https://github.com/InnoSoft-Company/InnoCaptcha"
    )
    parser.add_argument("--version", action="version", version=f"InnoCaptcha v{__version__}", help="Show the current version.")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # ---------------------------------------------------------
    # UPGRADE COMMAND
    # ---------------------------------------------------------
    subparsers.add_parser("upgrade", help="Upgrade InnoCaptcha to the latest version via pip.")
    
    # ---------------------------------------------------------
    # LOGS COMMAND
    # ---------------------------------------------------------
    logs_parser = subparsers.add_parser("logs", help="View security and operational logs.")
    logs_parser.add_argument("--tail", type=int, default=20, help="Number of log lines to show (default: 20).")
    
    # ---------------------------------------------------------
    # GENERATE COMMAND
    # ---------------------------------------------------------
    gen_parser = subparsers.add_parser("generate", help="Generate a new CAPTCHA challenge.")
    gen_parser.add_argument("type", choices=["text", "math", "audio", "voice", "image"], help="Type of CAPTCHA to generate.")
    gen_parser.add_argument("--output", "-o", help="Output file path to save the CAPTCHA image or audio file.")
    gen_parser.add_argument("--lang", choices=["en", "ar", "en-US", "ar-EG"], default="en", help="Language for the CAPTCHA (if applicable).")
    gen_parser.add_argument("--chars", help="Custom characters or phrase to use for the CAPTCHA.")
    gen_parser.add_argument("--ip", help="Client IP address to bind to the CAPTCHA.")
    gen_parser.add_argument("--session", help="Session ID to bind to the CAPTCHA.")
    
    # ---------------------------------------------------------
    # VERIFY COMMAND
    # ---------------------------------------------------------
    ver_parser = subparsers.add_parser("verify", help="Verify a generated CAPTCHA challenge.")
    ver_parser.add_argument("type", choices=["text", "math", "audio", "voice", "image"], help="Type of CAPTCHA to verify.")
    ver_parser.add_argument("--id", required=True, help="The unique ID of the CAPTCHA to verify.")
    ver_parser.add_argument("--answer", help="The user's answer (required for text, math, audio, image).")
    ver_parser.add_argument("--audio-file", help="Path to the user's recorded audio file (required for voice).")
    ver_parser.add_argument("--ip", help="Client IP address (must match the IP used during generation).")
    ver_parser.add_argument("--session", help="Session ID (must match the session used during generation).")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    if args.command == "upgrade":
        print("🚀 Upgrading InnoCaptcha...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "InnoCaptcha"])
            print("✅ Upgrade completed successfully!")
        except Exception as e:
            print(f"❌ Upgrade failed: {e}")
            sys.exit(1)

    elif args.command == "logs":
        if not os.path.exists(LOG_DIR):
            print("❌ No logs directory found.")
            return
        log_files = sorted([f for f in os.listdir(LOG_DIR) if f.endswith(".log")], reverse=True)
        if not log_files:
            print("❌ No log files found.")
            return
        latest_log = os.path.join(LOG_DIR, log_files[0])
        print(f"📄 --- Showing latest {args.tail} lines from {log_files[0]} ---")
        try:
            with open(latest_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines[-args.tail:]:
                    print(line.strip())
        except Exception as e:
            print(f"❌ Error reading logs: {e}")

    elif args.command == "generate":
        print(f"⚙️  Generating {args.type.upper()} CAPTCHA...")
        cid = None
        cap = None
        
        try:
            if args.type == "text":
                cap = TextCaptcha(lang=args.lang)
                cid = cap.create(chars=list(args.chars) if args.chars else None, ip=args.ip, session_id=args.session)
            elif args.type == "math":
                cap = MathCaptcha(output="image" if args.output else "text", lang=args.lang)
                cid = cap.create(ip=args.ip, session_id=args.session)
                if not args.output:
                    print(f"❓ Question: {cap.get_question()}")
            elif args.type == "audio":
                cap = AudioCaptcha(lang=args.lang)
                cid = cap.create(chars=list(args.chars) if args.chars else None, ip=args.ip, session_id=args.session)
            elif args.type == "voice":
                lang = args.lang if args.lang in ["en-US", "ar-EG"] else "en-US"
                cap = VoiceCaptcha(language=lang)
                cid = cap.create(phrase=args.chars, ip=args.ip, session_id=args.session)
                print(f"🗣️  Please read this phrase out loud: '{cap.phrase}'")
            elif args.type == "image":
                cap = ImageCaptcha(lang=args.lang)
                cid = cap.create(ip=args.ip, session_id=args.session)
                print(f"🔎 Target object to detect: '{cap.image_class}'")
                
            print(f"✅ CAPTCHA generated successfully! ID: {cid}")
            
            if args.output and hasattr(cap, "save"):
                cap.save(args.output)
                print(f"💾 Saved output to: {args.output}")
            elif args.output and args.type == "math":
                cap.get_question().save(args.output)
                print(f"💾 Saved math image to: {args.output}")
            elif args.type not in ["voice", "math"] and not args.output:
                print(f"⚠️  Warning: No --output specified. The CAPTCHA media was not saved.")
                
        except Exception as e:
            print(f"❌ Error generating CAPTCHA: {e}")
            sys.exit(1)

    elif args.command == "verify":
        print(f"🔍 Verifying {args.type.upper()} CAPTCHA...")
        cap = None
        try:
            if args.type == "text":
                cap = TextCaptcha(lang=args.lang if hasattr(args, 'lang') and args.lang else 'en')
            elif args.type == "math":
                cap = MathCaptcha(lang=args.lang if hasattr(args, 'lang') and args.lang else 'en')
            elif args.type == "audio":
                cap = AudioCaptcha(lang=args.lang if hasattr(args, 'lang') and args.lang else 'en')
            elif args.type == "voice":
                lang = args.lang if hasattr(args, 'lang') and args.lang in ["en-US", "ar-EG"] else "en-US"
                cap = VoiceCaptcha(language=lang)
            elif args.type == "image":
                cap = ImageCaptcha(lang=args.lang if hasattr(args, 'lang') and args.lang else 'en')
                
            cap.id = args.id
            
            if args.type == "voice":
                if not args.audio_file:
                    print("❌ Error: --audio-file is required to verify a voice CAPTCHA.")
                    sys.exit(1)
                with open(args.audio_file, "rb") as f:
                    audio_bytes = f.read()
                result = cap.verify(audio_bytes, ip=args.ip, session_id=args.session)
            else:
                if not args.answer:
                    print(f"❌ Error: --answer is required to verify a {args.type} CAPTCHA.")
                    sys.exit(1)
                result = cap.verify(args.answer, ip=args.ip, session_id=args.session)
                
            if result is True:
                print("✅ Verification SUCCESS! The answer is correct.")
            else:
                print(f"❌ Verification FAILED: {result}")
        except FileNotFoundError:
            print(f"❌ Error: File not found.")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error during verification: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
