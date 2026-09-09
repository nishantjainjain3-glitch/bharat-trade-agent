import uvicorn
import socket
import os
from dotenv import load_dotenv

load_dotenv()

def get_local_network_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

if __name__ == "__main__":
    local_ip = get_local_network_ip()
    print("=" * 65)
    print("  BHARAT TRADE AGENT - Indian Stock Market Workstation")
    print("=" * 65)
    print(f"  * Desktop Access:   http://localhost:8000")
    print(f"  * Mobile Phone:     http://{local_ip}:8000")
    print("=" * 65)
    print("  Starting server on 0.0.0.0:8000 ... (Press Ctrl+C to stop)\n")
    uvicorn.run("src.api.server:app", host="0.0.0.0", port=8000, reload=False)
