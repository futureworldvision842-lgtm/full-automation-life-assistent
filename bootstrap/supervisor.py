"""
JARVIS portable supervisor.

Launches AND keeps alive the JARVIS core on ANY machine — paths are derived
from this file's location and the Python interpreter running it, so no absolute
paths are hard-coded. Each component runs in its own detached console (survives
this process) and is relaunched automatically if it dies.

Run via run.bat (which points a venv/python at this file). This is what the
Startup shortcut / desktop button launch so that on every boot JARVIS + all its
in-repo services come up and stay up.
"""
import os
import shutil
import socket
import subprocess
import sys
import time

# Repo root = parent of this bootstrap/ folder. Everything is relative to it.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable  # the (venv) python that launched us
NEW_CONSOLE = 0x00000010  # CREATE_NEW_CONSOLE — detached window that persists

# Manual-stop flag: when present, the user deliberately stopped Jarvis, so the
# Voice GUI must NOT be auto-relaunched until they open it again (Start clears it).
STOP_FLAG = os.path.join(ROOT, "scratch", "jarvis.stop")

# Keep the existing model library when present and give agentic sessions enough
# server-side context. These values affect only the supervised Ollama process.
shared_ollama_models = os.path.join(os.path.dirname(ROOT), "ollama", "models")
os.environ.setdefault("OLLAMA_MODELS", shared_ollama_models if os.path.isdir(shared_ollama_models) else os.path.join(ROOT, "scratch", "ollama", "models"))
os.environ.setdefault("OLLAMA_CONTEXT_LENGTH", "65536")
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "24h")

try:
    import psutil
except Exception:
    psutil = None


def port_up(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.3)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False
    finally:
        s.close()


def proc_running(needle):
    if psutil is None:
        return True  # can't check — assume up rather than spawn duplicates
    # Only count python/node executables — otherwise any shell command that
    # merely mentions the needle (e.g. a grep for 'main.py') looks like the GUI.
    for p in psutil.process_iter(["name", "cmdline"]):
        try:
            nm = (p.info.get("name") or "").lower()
            if not (nm.startswith("python") or nm.startswith("node")):
                continue
            if needle in " ".join(p.info.get("cmdline") or []):
                return True
        except Exception:
            continue
    return False


def have(exe):
    return shutil.which(exe) is not None


def _p(*parts):
    return os.path.join(ROOT, *parts)


def build_services():
    """Only include components whose files/tools actually exist on this machine."""
    node = "node" if have("node") else None
    svcs = []

    # Voice + brain GUI (the heart of JARVIS)
    if os.path.exists(_p("main.py")):
        svcs.append(("Voice GUI", "proc", "main.py", [PY, "main.py"], ROOT))

    # Ops dashboard (world monitor, PC vitals, activity) — http://localhost:8770
    if os.path.exists(_p("dashboard.py")):
        svcs.append(("Dashboard", "port", 8770, [PY, "dashboard.py"], ROOT))

    # Phone remote — http://localhost:8765
    if os.path.exists(_p("mobile_control.py")):
        svcs.append(("Mobile", "port", 8765, [PY, "mobile_control.py"], ROOT))

    # Status-only local bridge and cloud heartbeat used by the GAIGS app.
    if os.path.exists(_p("web", "server.py")):
        svcs.append(("GAIGS Bridge", "port", 8090, [PY, "server.py"], _p("web")))
    if os.path.exists(_p("web", "heartbeat_reporter.py")):
        svcs.append(("GAIGS Heartbeat", "proc", "heartbeat_reporter.py", [PY, "heartbeat_reporter.py"], _p("web")))

    # Read-only daily mission health, memory and owner WhatsApp briefing.
    if os.path.exists(_p("agent", "mission_daemon.py")):
        svcs.append(("Mission Control", "proc", "mission_daemon.py", [PY, "mission_daemon.py"], _p("agent")))

    # WhatsApp bridge (Baileys) — port 3200. Needs node + npm install done.
    if node and os.path.exists(_p("wa", "jarvis_baileys.js")) and os.path.isdir(_p("wa", "node_modules")):
        svcs.append(("WhatsApp", "port", 3200, [node, "jarvis_baileys.js"], _p("wa")))

    # Local LLM (optional). Uses ollama on PATH, or a copy under scratch/ollama.
    ollama = "ollama" if have("ollama") else None
    local_ollama = _p("scratch", "ollama", "ollama.exe")
    if not ollama and os.path.exists(local_ollama):
        ollama = local_ollama
    if ollama:
        svcs.append(("Ollama", "port", 11434, [ollama, "serve"], os.path.dirname(ollama) if os.path.isabs(ollama) else ROOT))

    # ---- Optional external bots (installed by install_extras.bat) ----

    # Moltbot / clawdbot gateway — installed globally via npm.
    if have("clawdbot"):
        svcs.append(("Moltbot", "port", 18789, ["cmd", "/c", "clawdbot gateway run --port 18789 --bind loopback --allow-unconfigured"], ROOT))

    # Odysseus AI server — cloned into bots/odysseus (FastAPI on 7000).
    ody = _p("bots", "odysseus", "app.py")
    if os.path.exists(ody):
        svcs.append(("Odysseus", "port", 7000,
                     [PY, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "7000"],
                     _p("bots", "odysseus")))

    return svcs


def spawn(name, cmd, cwd):
    try:
        subprocess.Popen(cmd, cwd=cwd, creationflags=NEW_CONSOLE)
        print(f"[Supervisor] launched {name}")
    except Exception as e:
        print(f"[Supervisor] {name} launch error: {e}")


def alive(kind, key):
    return port_up(key) if kind == "port" else proc_running(key)


def main():
    if os.path.exists(STOP_FLAG):
        print("[Supervisor] Manual stop is active. Open JARVIS normally to clear it.")
        return
    services = build_services()
    print(f"[Supervisor] JARVIS supervisor online. Root: {ROOT}")
    print("[Supervisor] Managing: " + ", ".join(s[0] for s in services))
    first = True
    while True:
        manual_stop = os.path.exists(STOP_FLAG)
        if manual_stop:
            print("[Supervisor] Owner stop detected. Supervisor is exiting and will not relaunch services.")
            return
        for name, kind, key, cmd, cwd in services:
            try:
                if not alive(kind, key):
                    if not first:
                        print(f"[Supervisor] {name} is down — relaunching")
                    spawn(name, cmd, cwd)
                    time.sleep(3 if name in ("Ollama", "Voice GUI") else 1.5)
            except Exception as e:
                print(f"[Supervisor] check {name} error: {e}")
        first = False
        time.sleep(10)


if __name__ == "__main__":
    main()
