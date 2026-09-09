import os
import subprocess
import urllib.request
import re
import sys

CLOUDFLARED_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
LOCAL_EXE = os.path.join(os.path.dirname(__file__), "cloudflared.exe")

def ensure_cloudflared():
    if not os.path.exists(LOCAL_EXE):
        print("[+] Downloading standalone Cloudflare Tunnel client (free-for-dev) ...")
        urllib.request.urlretrieve(CLOUDFLARED_URL, LOCAL_EXE)
        print("[+] Download complete.")

def start_tunnel():
    ensure_cloudflared()
    print("\n" + "=" * 60)
    print("  CREATING FREE SECURE PUBLIC URL FOR YOUR PHONE")
    print("=" * 60)
    print("  Target: http://localhost:8000")
    print("  Starting Cloudflare Tunnel...\n")
    
    proc = subprocess.Popen(
        [LOCAL_EXE, "tunnel", "--url", "http://localhost:8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    url_found = False
    for line in iter(proc.stdout.readline, ""):
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match and not url_found:
            public_url = match.group(0)
            url_found = True
            print("=" * 60)
            print(f"  SUCCESS! Open this URL on your phone from ANYWHERE:")
            print(f"  >>> {public_url} <<<")
            print("=" * 60)
            print("  (Works on mobile 4G/5G, office Wi-Fi, or travel)\n")
            print("  Press Ctrl+C to close the tunnel.\n")
            
    proc.wait()

if __name__ == "__main__":
    start_tunnel()
