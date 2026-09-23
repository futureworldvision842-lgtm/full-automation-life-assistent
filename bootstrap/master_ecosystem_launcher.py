"""
bootstrap/master_ecosystem_launcher.py — 100% Bulletproof J.A.R.V.I.S. Master Launcher
========================================================================================
Manages Full Fleet & Granular Single-Service ON/OFF/RESTART across:
  1. Master Operations Command Center     (Port 8770)
  2. God's Eye View 3D Globe Console      (Port 4173)
  3. Native World Monitor Situational UI  (Port 3000)
  4. MQ3 Multi-Account Trading Cockpit    (Port 5050)
  5. Odysseus Autonomous AI Brain Server  (Port 7000)
  6. Mobile Companion & Screen Gateway    (Port 8765)
  7. 24/7 Autonomous Live Trading Daemon  (Pipdance $1k + FTMO $100k)
  8. Ollama Local Offline LLM Node        (Port 11434)
========================================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional

# Enforce UTF-8 on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import psutil
except ImportError:
    psutil = None

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
LOG_DIR = ROOT / "logs" / "services"
RUNTIME_DIR = ROOT / "runtime"
STOP_FLAG = ROOT / "scratch" / "jarvis.stop"
LOCK_FILE = RUNTIME_DIR / "supervisor.lock"

# Python interpreter selection
if (ROOT / ".venv" / "Scripts" / "python.exe").exists():
    PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
elif Path(r"F:\Jarvis Command Center\.venv\Scripts\python.exe").exists():
    PY = r"F:\Jarvis Command Center\.venv\Scripts\python.exe"
elif Path(r"C:\Python314\python.exe").exists():
    PY = r"C:\Python314\python.exe"
else:
    PY = sys.executable

# Paths to subsystems
WORLD_MONITOR_ROOT = Path("F:/worldmonitor-main") if Path("F:/worldmonitor-main").exists() else ROOT / "worldmonitor-main"
GODS_EYE_VIEW_ROOT = ROOT / "gods-eye-view"
MQ3_ROOT = ROOT / "MQ3 TRADING BOT"
ODYSSEUS_ROOT = ROOT / "bots" / "odysseus"

SERVICES: Dict[str, Dict[str, Any]] = {
    "dashboard": {
        "key": "dashboard",
        "name": "Master Dashboard",
        "port": 8770,
        "url": "http://127.0.0.1:8770",
        "cmd": [PY, "dashboard.py"],
        "cwd": str(ROOT),
        "log": LOG_DIR / "dashboard.log",
        "match": "dashboard.py",
    },
    "godseye": {
        "key": "godseye",
        "name": "God's Eye View 3D Globe",
        "port": 4173,
        "url": "http://127.0.0.1:4173/",
        "cmd": ["node", "node_modules/vite/bin/vite.js", "--port", "4173", "--host", "127.0.0.1"],
        "cwd": str(GODS_EYE_VIEW_ROOT),
        "log": LOG_DIR / "gods-eye-view.log",
        "match": "gods-eye-view",
    },
    "worldmonitor": {
        "key": "worldmonitor",
        "name": "Native World Monitor Radar",
        "port": 3000,
        "url": "http://127.0.0.1:3000",
        "cmd": ["node", "node_modules/vite/bin/vite.js", "--port", "3000", "--host", "127.0.0.1"],
        "cwd": str(WORLD_MONITOR_ROOT),
        "log": LOG_DIR / "world-monitor.log",
        "match": "worldmonitor",
    },
    "mq3": {
        "key": "mq3",
        "name": "MQ3 Trading Cockpit",
        "port": 5050,
        "url": "http://127.0.0.1:5050/api/status",
        "cmd": [PY, "run.py", "--demo", "--host", "127.0.0.1", "--port", "5050"],
        "cwd": str(MQ3_ROOT),
        "log": LOG_DIR / "mq3.log",
        "match": "run.py",
    },
    "odysseus": {
        "key": "odysseus",
        "name": "Odysseus AI Brain Server",
        "port": 7000,
        "url": "http://127.0.0.1:7000/api/health",
        "cmd": [PY, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "7000"],
        "cwd": str(ODYSSEUS_ROOT),
        "log": LOG_DIR / "odysseus.log",
        "match": "uvicorn",
    },
    "mobile": {
        "key": "mobile",
        "name": "Mobile Remote Gateway",
        "port": 8765,
        "url": "http://127.0.0.1:8765/api/health",
        "cmd": [PY, "mobile_control.py"],
        "cwd": str(ROOT),
        "log": LOG_DIR / "mobile.log",
        "match": "mobile_control.py",
    },
    "trader": {
        "key": "trader",
        "name": "Autonomous Live Trading Daemon",
        "port": 0,
        "url": None,
        "cmd": [PY, "src/autonomous_live_daemon.py"],
        "cwd": str(MQ3_ROOT),
        "log": LOG_DIR / "autonomous_live_daemon.log",
        "match": "autonomous_live_daemon.py",
    },
    "ollama": {
        "key": "ollama",
        "name": "Ollama Local AI Node",
        "port": 11434,
        "url": "http://127.0.0.1:11434/api/tags",
        "cmd": ["ollama", "serve"],
        "cwd": str(ROOT),
        "log": LOG_DIR / "ollama.log",
        "match": "ollama",
    },
    "discord": {
        "key": "discord",
        "name": "Discord Intelligence Bot",
        "port": 0,
        "url": None,
        "cmd": [PY, "bots/discord_bot.py"],
        "cwd": str(ROOT),
        "log": LOG_DIR / "discord.log",
        "match": "discord_bot.py",
    },
    "whatsapp": {
        "key": "whatsapp",
        "name": "WhatsApp Baileys Bridge",
        "port": 3200,
        "url": "http://127.0.0.1:3200/status",
        "cmd": ["node.exe", "jarvis_baileys.js"],
        "cwd": str(ROOT / "wa"),
        "log": LOG_DIR / "whatsapp.log",
        "match": "jarvis_baileys",
    },
}

SERVICE_ALIASES = {
    "all": "all",
    "dashboard": "dashboard",
    "godseye": "godseye",
    "gods-eye": "godseye",
    "gods_eye": "godseye",
    "gods_eye_view": "godseye",
    "worldmonitor": "worldmonitor",
    "world_monitor": "worldmonitor",
    "wm": "worldmonitor",
    "mq3": "mq3",
    "trading": "trader",
    "trader": "trader",
    "bot": "trader",
    "daemon": "trader",
    "odysseus": "odysseus",
    "mobile": "mobile",
    "ollama": "ollama",
    "discord": "discord",
    "dc": "discord",
    "whatsapp": "whatsapp",
    "wa": "whatsapp",
}


def is_port_open(port: int, timeout: float = 0.4) -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def probe_http(url: str, timeout: float = 1.0) -> bool:
    if not url:
        return False
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "JarvisLauncher/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def is_process_running(pattern: str) -> bool:
    if not pattern:
        return False
    pat = pattern.lower()
    if psutil:
        try:
            for p in psutil.process_iter(["name", "cmdline"]):
                try:
                    cmd = " ".join(p.info["cmdline"] or []).lower()
                    if pat in cmd:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            return False
        except Exception:
            pass

    # Fallback via PowerShell
    try:
        ps_cmd = f"Get-Process -ErrorAction SilentlyContinue | Where-Object {{ $_.CommandLine -like '*{pat}*' }} | Measure-Object | Select-Object -ExpandProperty Count"
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return int(res.stdout.strip() or "0") > 0
    except Exception:
        return False


def kill_by_port(port: int):
    if port <= 0:
        return
    from bootstrap.lifecycle import get_pids_on_port, kill_process_tree
    pids = get_pids_on_port(port)
    for pid in pids:
        kill_process_tree(pid)


def kill_by_pattern(pattern: str):
    if not pattern:
        return
    pat = pattern.lower()
    from bootstrap.lifecycle import kill_process_tree
    if psutil:
        try:
            for p in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmd = " ".join(p.info["cmdline"] or []).lower()
                    if pat in cmd and p.pid != os.getpid():
                        kill_process_tree(p.pid)
                except Exception:
                    pass
        except Exception:
            pass


def is_service_online(svc_key: str) -> bool:
    svc = SERVICES.get(svc_key)
    if not svc:
        return False
    if svc["port"] > 0:
        if svc["url"]:
            return probe_http(svc["url"])
        return is_port_open(svc["port"])
    return is_process_running(svc["match"])


def get_fleet_status() -> Dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor
    def check(key_svc):
        key, svc = key_svc
        online = is_service_online(key)
        return key, {
            "key": key,
            "name": svc["name"],
            "port": svc["port"],
            "url": svc["url"],
            "online": online,
            "healthy": online,
            "status": "ONLINE" if online else "OFFLINE",
        }
    with ThreadPoolExecutor(max_workers=len(SERVICES)) as pool:
        results = dict(pool.map(check, SERVICES.items()))
    return results


def _safe_specs():
    from bootstrap.supervisor import build_services
    by_port = {svc['port']: key for key, svc in SERVICES.items() if svc['port'] > 0}
    return {by_port.get(spec['port'], 'globe_mobile'): spec for spec in build_services()}


def _set_disabled(names, disabled):
    from bootstrap.supervisor import OVERRIDES_FILE
    try:
        current = set(json.loads(OVERRIDES_FILE.read_text(encoding='utf-8')).get('disabled', []))
    except (OSError, ValueError, TypeError):
        current = set()
    current.update(names) if disabled else current.difference_update(names)
    OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = OVERRIDES_FILE.with_name(OVERRIDES_FILE.name + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps({'disabled': sorted(current)}), encoding='utf-8')
    os.replace(temporary, OVERRIDES_FILE)


def _observed(spec):
    from bootstrap.supervisor import probe, read_state
    url = 'http://127.0.0.1:' + str(spec['port']) + spec['path']
    result = probe(url)
    rec = read_state().get('services', {}).get(spec['name'], {})
    return {'name': spec['name'], 'url': url, 'online': result.get('ready', False),
            'healthy': result.get('ready', False), 'owned': bool(rec.get('owned')),
            'status': rec.get('status', 'observed-external'), 'http_status': result.get('http_status')}


def start_service(svc_key: str):
    canonical = SERVICE_ALIASES.get(svc_key.lower(), svc_key.lower())
    if canonical == 'all':
        return start_all_services(open_browser=False)
    spec = _safe_specs().get(canonical)
    if spec is None:
        return {'ok': False, 'executed': False, 'error': 'Service disabled or unknown; autonomous trading and broadcasts require separate review.'}
    _set_disabled([spec['name']], False)
    from bootstrap.control import start_supervisor
    started = start_supervisor(wait=10)
    if not started['ok']:
        return started
    deadline = time.monotonic() + 25
    result = _observed(spec)
    while not result['healthy'] and time.monotonic() < deadline:
        time.sleep(0.5)
        result = _observed(spec)
    return {'ok': result['healthy'], **result, 'message': 'Service HTTP readiness verified.' if result['healthy'] else 'Service not ready; inspect its log.'}


def stop_service(svc_key: str):
    canonical = SERVICE_ALIASES.get(svc_key.lower(), svc_key.lower())
    if canonical == 'all':
        return stop_all_services()
    spec = _safe_specs().get(canonical)
    if not spec:
        return {'ok': False, 'error': 'Not a managed safe-fleet service.'}
    _set_disabled([spec['name']], True)
    from bootstrap.lifecycle import stop_recorded_services
    result = stop_recorded_services([spec['name']])
    observed = _observed(spec)
    result.update(name=spec['name'], online=observed['online'])
    result['ok'] = result['ok'] and not observed['online']
    result['message'] = 'Recorded service stopped.' if result['ok'] else 'An external or current caller process remains; no unrecorded process was killed.'
    return result


def restart_service(svc_key: str):
    stopped = stop_service(svc_key)
    return start_service(svc_key) if stopped.get('ok') else stopped


def stop_all_services(include_dashboard=True):
    from bootstrap.lifecycle import stop_managed_processes
    if include_dashboard:
        return stop_managed_processes()
    results = {key: stop_service(key) for key in _safe_specs() if key != 'dashboard'}
    return {'ok': all(r.get('ok') for r in results.values()), 'services': results}


def start_all_services(open_browser=True, daemon=False, wait=40):
    """One supervisor owns all children; no fake success, port kills or live daemon."""
    specs = _safe_specs()
    _set_disabled([spec['name'] for spec in specs.values()], False)
    from bootstrap.control import start_supervisor
    started = start_supervisor(wait=10)
    if not started['ok']:
        return started
    deadline = time.monotonic() + max(0, min(float(wait), 60))
    from concurrent.futures import ThreadPoolExecutor
    while True:
        with ThreadPoolExecutor(max_workers=len(specs)) as pool:
            observed = dict(pool.map(lambda item: (item[0], _observed(item[1])), specs.items()))
        if all(r['healthy'] for r in observed.values()) or time.monotonic() >= deadline:
            break
        time.sleep(0.5)
    if open_browser and observed.get('dashboard', {}).get('healthy'):
        webbrowser.open('http://127.0.0.1:8770/')
    return {'ok': all(r['healthy'] for r in observed.values()), 'fleet': observed,
            'disabled': ['autonomous-trading', 'discord', 'unattended-broadcasts'],
            'message': 'HTTP readiness only; provider data and device permissions require independent checks.'}


def print_status():
    print("================================================================================")
    print("   J.A.R.V.I.S. SOVEREIGN FLEET STATUS AUDIT")
    print("================================================================================")
    status_map = get_fleet_status()
    for key, s in status_map.items():
        state = "[ONLINE]" if s["online"] else "[OFFLINE]"
        port_info = f":{s['port']}" if s["port"] > 0 else "DAEMON"
        print(f"  {state:10} {s['name']:32} {port_info:15} -> {s['url'] or 'Internal'}")
    print("================================================================================")


def main():
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. Master Ecosystem Launcher")
    parser.add_argument("action", nargs="?", default="start", choices=["start", "stop", "restart", "status"])
    parser.add_argument("service", nargs="?", default="all", help="Target service: all, godseye, worldmonitor, mq3, odysseus, mobile, trader, dashboard, ollama")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser windows on start")
    parser.add_argument("--daemon", action="store_true", help="Keep master supervisor monitoring loop alive in background")
    parser.add_argument("--json", action="store_true", help="Output status in JSON format")
    args = parser.parse_args()

    target = SERVICE_ALIASES.get(args.service.lower(), args.service.lower())

    if args.action == "status":
        if args.json:
            print(json.dumps(get_fleet_status(), indent=2))
        else:
            print_status()
    elif args.action == "start":
        if target == "all":
            start_all_services(open_browser=not args.no_browser, daemon=args.daemon)
        else:
            res = start_service(target)
            print(json.dumps(res, indent=2))
    elif args.action == "stop":
        if target == "all":
            stop_all_services()
        else:
            res = stop_service(target)
            print(json.dumps(res, indent=2))
    elif args.action == "restart":
        if target == "all":
            stop_all_services()
            time.sleep(1.5)
            start_all_services(open_browser=not args.no_browser, daemon=args.daemon)
        else:
            res = restart_service(target)
            print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
