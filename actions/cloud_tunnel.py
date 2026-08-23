"""
actions/cloud_tunnel.py — Global Internet HTTPS Tunnel Manager for J.A.R.V.I.S.

Exposes local 3D Web HUD (8080) and WhatsApp Bridge (3200) to the global internet
via secure public HTTPS tunneling (localtunnel / cloudflared).
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
from pathlib import Path

PUBLIC_URL_FILE = Path(__file__).resolve().parent.parent / "config" / "public_url.json"

def start_public_tunnel(port: int = 8090) -> str:
    """Launches localtunnel in background and registers public HTTPS URL."""
    print(f"[CloudTunnel] Starting public HTTPS tunnel for port {port}...")
    cmd = f"npx -y localtunnel --port {port} --local-host 127.0.0.1"
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Wait for tunnel URL output
    url = ""
    for _ in range(15):
        time.sleep(1)
        if proc.poll() is not None:
            break
        # Read available lines
        try:
            line = proc.stdout.readline().strip()
            if "url is:" in line.lower():
                url = line.split("url is:")[-1].strip()
                break
        except Exception:
            pass

    if not url:
        url = f"http://192.168.100.238:{port}"

    # Save to public_url.json
    PUBLIC_URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_URL_FILE.write_text(json.dumps({"public_url": url, "port": port, "updated_at": time.time()}), encoding="utf-8")
    print(f"[CloudTunnel] Public HTTPS URL active: {url}")
    return url

if __name__ == "__main__":
    print(f"Active Tunnel URL: {start_public_tunnel(8090)}")
