import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def check_config():
    warnings = []
    if not os.getenv("GROQ_API_KEY"):
        warnings.append("⚠️  GROQ_API_KEY manquante → https://console.groq.com (gratuit)")
    if not os.getenv("PLANTNET_API_KEY"):
        warnings.append("⚠️  PLANTNET_API_KEY manquante → https://my.plantnet.org (gratuit)")
    if warnings:
        print("\n" + "="*50)
        print("CONFIGURATION INCOMPLÈTE :")
        for w in warnings:
            print(w)
        print("Crée le fichier .env avec tes clés.")
        print("="*50 + "\n")
    else:
        print("✅ Configuration OK — Slothia démarré !")

check_config()


if not any("streamlit" in arg for arg in sys.argv):
    app_path = str(Path(__file__).parent / "app.py")
    sys.exit(subprocess.call([
        sys.executable, "-m", "streamlit", "run", app_path
    ]))
else:
    import app