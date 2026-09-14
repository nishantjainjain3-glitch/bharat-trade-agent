import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

project_dir = Path(__file__).resolve().parent.parent
env_path = project_dir / ".env"
load_dotenv(dotenv_path=env_path)

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not token or not chat_id:
    print("Telegram token or chat_id not found in .env")
    sys.exit(1)

message = (
    "GOOD MORNING! 🌅\n\n"
    "It is 08:45 AM IST. Time to open your laptop!\n\n"
    "Indian stock markets open in 30 minutes at 09:15 AM IST.\n\n"
    "Staged Watchlist Targets:\n"
    "1. BHEL (Entry: ₹431.00, Stop: ₹406.10, Target: ₹487.02)\n"
    "2. City Union Bank (CUB) (Entry: ₹227.32)\n"
    "3. Federal Bank (FEDERALBNK) (Entry: ₹344.50)\n\n"
    "Pre-market radar and dashboard live at:\n"
    "http://localhost:8000"
)

try:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print("Telegram alert sent successfully:", res.get("ok"))
except Exception as e:
    print("Failed to send Telegram alert:", str(e))
