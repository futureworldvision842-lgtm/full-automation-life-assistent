"""
actions/persistent_tunnel.py — 24/7 Persistent Auto-Reconnecting Cloud Tunnel Daemon
=====================================================================================
Ensures J.A.R.V.I.S. Sovereign Mobile Companion & Satellite Hub (port 8765)
is ALWAYS accessible over public HTTPS globally (WAN / 4G / 5G / cellular data).
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_URL_FILE = CONFIG_DIR / "public_url.json"
TARGET_PORT = int(os.getenv("JARVIS_TUNNEL_PORT", "8765"))


def get_active_tunnel_url() -> str:
    """Returns currently registered public HTTPS URL from config."""
    if PUBLIC_URL_FILE.exists():
        try:
            data = json.loads(PUBLIC_URL_FILE.read_text(encoding="utf-8"))
            return data.get("public_url", "")
        except Exception:
            pass
    return ""


def write_tunnel_state(url: str, port: int, status: str = "ONLINE") -> None:
    """Writes the active tunnel state to config/public_url.json."""
    try:
        payload = {
            "public_url": url,
            "port": port,
            "updated_at": time.time(),
            "status": status,
            "tunnel_type": "localtunnel" if "loca.lt" in url else "cloudflared"
        }
        PUBLIC_URL_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[PersistentTunnel] Public HTTPS Tunnel State Saved: {url} (Port {port})", flush=True)
    except Exception as e:
        print(f"[PersistentTunnel] Failed to write state file: {e}", flush=True)


def verify_tunnel_health(url: str) -> bool:
    """Checks if public HTTPS tunnel URL is responsive (returns 200 or valid response)."""
    if not url or not url.startswith("http"):
        return False
    try:
        check_url = f"{url.rstrip('/')}/api/health"
        req = urllib.request.Request(
            check_url,
            headers={
                "Bypass-Tunnel-Reminder": "true",
                "User-Agent": "JarvisTunnelWatchdog/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in (200, 303, 307)
    except urllib.error.HTTPError as he:
        # If server returns 401 or 403 or 404, it means the server is UP and answering!
        return he.code in (200, 401, 403, 404, 303)
    except Exception:
        return False


def start_tunnel_process(port: int = 8765) -> tuple[Optional[subprocess.Popen], str]:
    """Launches localtunnel subprocess and captures the assigned public HTTPS URL."""
    print(f"[PersistentTunnel] Spawning localtunnel for port {port}...", flush=True)
    cmd = ["cmd.exe", "/c", "npx.cmd", "-y", "localtunnel", "--port", str(port), "--local-host", "127.0.0.1"]
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"[PersistentTunnel] Process spawn failed: {e}", flush=True)
        return None, ""

    url = ""
    start_time = time.time()
    while time.time() - start_time < 20:
        if proc.poll() is not None:
            print(f"[PersistentTunnel] Subprocess exited early with code {proc.returncode}", flush=True)
            break
        try:
            line = proc.stdout.readline()
            if not line:
                time.sleep(0.3)
                continue
            line_str = line.strip()
            print(f"[TunnelLog] {line_str}", flush=True)
            if "url is:" in line_str.lower():
                url = line_str.split("url is:")[-1].strip()
                break
            m = re.search(r'https://[a-zA-Z0-9-]+\.loca\.lt', line_str)
            if m:
                url = m.group(0)
                break
        except Exception:
            pass

    return proc, url


def run_daemon_loop(port: int = 8765):
    """24/7 background watchdog maintaining persistent public tunnel."""
    print(f"[PersistentTunnel] J.A.R.V.I.S. 24/7 Global Cloud Tunnel Starting on Port {port}...", flush=True)
    
    current_proc: Optional[subprocess.Popen] = None
    current_url: str = ""

    def cleanup(signum=None, frame=None):
        nonlocal current_proc
        print("[PersistentTunnel] Shutting down tunnel daemon...", flush=True)
        if current_proc and current_proc.poll() is None:
            current_proc.terminate()
        sys.exit(0)

    try:
        signal.signal(signal.SIGINT, cleanup)
        signal.signal(signal.SIGTERM, cleanup)
    except Exception:
        pass

    consecutive_failures = 0

    while True:
        try:
            # If no active tunnel or process dead, restart
            if not current_proc or current_proc.poll() is not None or not current_url:
                if current_proc and current_proc.poll() is None:
                    try:
                        current_proc.terminate()
                        current_proc.wait(timeout=3)
                    except Exception:
                        pass

                current_proc, current_url = start_tunnel_process(port)
                if current_url:
                    write_tunnel_state(current_url, port, status="ONLINE")
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    sleep_time = min(30, 5 * consecutive_failures)
                    print(f"[PersistentTunnel] Tunnel spawn attempt failed ({consecutive_failures}). Retrying in {sleep_time}s...", flush=True)
                    time.sleep(sleep_time)
                    continue

            # Check health
            time.sleep(25)
            healthy = verify_tunnel_health(current_url)
            if healthy:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                print(f"[PersistentTunnel] Health check warning ({consecutive_failures}/3) for {current_url}", flush=True)
                if consecutive_failures >= 3:
                    print(f"[PersistentTunnel] Tunnel unresponsive. Resetting tunnel...", flush=True)
                    if current_proc and current_proc.poll() is None:
                        current_proc.terminate()
                    current_proc = None
                    current_url = ""
                    consecutive_failures = 0

        except Exception as ex:
            print(f"[PersistentTunnel] Watchdog iteration exception: {ex}", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else TARGET_PORT
    run_daemon_loop(port_arg)
