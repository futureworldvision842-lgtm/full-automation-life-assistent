"""
actions/persistent_tunnel.py — 24/7 Persistent Auto-Reconnecting Cloud Tunnel Daemon
Ensures J.A.R.V.I.S. 3D Web HUD (port 8080) is ALWAYS accessible over public HTTPS without 503 errors.
"""

import os
import sys
import time
import json
import subprocess
import urllib.request
from pathlib import Path

PUBLIC_URL_FILE = Path(__file__).resolve().parent.parent / "config" / "public_url.json"

def get_active_tunnel_url() -> str:
    """Returns currently registered public HTTPS URL."""
    if PUBLIC_URL_FILE.exists():
        try:
            data = json.loads(PUBLIC_URL_FILE.read_text(encoding="utf-8"))
            return data.get("public_url", "")
        except Exception:
            pass
    return ""

def verify_tunnel_health(url: str) -> bool:
    """Checks if public HTTPS tunnel URL is responsive (returns non-503)."""
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers={"Bypass-Tunnel-Reminder": "true", "User-Agent": "JarvisMonitor"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except Exception:
        return False

def start_persistent_tunnel_loop(port: int = 8080):
    """Background loop that maintains an active, auto-reconnecting Cloud HTTPS Tunnel."""
    print(f"[PersistentTunnel] Initializing 24/7 Auto-Reconnecting Cloud Tunnel on port {port}...")
    
    while True:
        current_url = get_active_tunnel_url()
        
        # Check health
        if current_url and verify_tunnel_health(current_url):
            time.sleep(30)
            continue
            
        print("[PersistentTunnel] Tunnel dropped or unavailable. Reconnecting new HTTPS tunnel...")
        cmd = f"npx -y localtunnel --port {port} --local-host 127.0.0.1"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        new_url = ""
        for _ in range(12):
            time.sleep(1)
            try:
                line = proc.stdout.readline().strip()
                if "url is:" in line.lower():
                    new_url = line.split("url is:")[-1].strip()
                    break
            except Exception:
                pass

        if new_url:
            PUBLIC_URL_FILE.parent.mkdir(parents=True, exist_ok=True)
            PUBLIC_URL_FILE.write_text(json.dumps({
                "public_url": new_url,
                "port": port,
                "updated_at": time.time()
            }), encoding="utf-8")
            print(f"[PersistentTunnel] Public HTTPS Tunnel re-established: {new_url}")
        else:
            print("[PersistentTunnel] Reconnect attempt pending. Retrying in 10s...")
            time.sleep(10)

if __name__ == "__main__":
    start_persistent_tunnel_loop(8080)
