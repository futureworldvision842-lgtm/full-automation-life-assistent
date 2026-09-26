"""Local supervisor with process ownership, HTTP readiness and bounded restarts."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
import psutil
import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from platform_runtime import WORLD_MONITOR_ROOT, MQ3_ROOT, GODS_EYE_VIEW_ROOT, mq3_dashboard_port
STATE_FILE = ROOT / "runtime" / "supervisor-state.json"
LOCK_FILE = ROOT / "runtime" / "supervisor.lock"
STOP_FLAG = ROOT / "scratch" / "jarvis.stop"
OVERRIDES_FILE = ROOT / 'runtime/service-overrides.json'
LOG_DIR = ROOT / "logs" / "services"
PY = getattr(sys, "_base_executable", sys.executable)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def identity(pid):
    proc = psutil.Process(pid)
    return {"pid": proc.pid, "created": proc.create_time()}


def matching_process(entry):
    """PID alone is insufficient: Windows may have reused it."""
    try:
        proc = psutil.Process(int(entry["pid"]))
        return proc if abs(proc.create_time() - float(entry["created"])) < 0.01 and proc.is_running() else None
    except (KeyError, ValueError, TypeError, psutil.Error):
        return None


def proc_running(needle: str) -> bool:
    """Check if any running process matches the given pattern in its command line."""
    if not needle:
        return False
    needle_lower = needle.lower()
    try:
        for p in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmd = " ".join(p.info.get("cmdline") or []).lower()
                if needle_lower in cmd:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass
    return False


def read_state():
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if value.get("root") == str(ROOT) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def write_state(value):
    """Publish atomically; a brief Windows reader lock must not kill supervision."""
    temp = STATE_FILE.with_name(f"{STATE_FILE.name}.{os.getpid()}.tmp")
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp.write_text(json.dumps(value, indent=2), encoding="utf-8")
        for attempt in range(8):
            try:
                os.replace(temp, STATE_FILE)
                return True
            except PermissionError:
                time.sleep(0.05 * (attempt + 1))
        # Fallback to direct overwrite if atomic replace had a share lock
        try:
            STATE_FILE.write_text(json.dumps(value, indent=2), encoding="utf-8")
            return True
        except Exception:
            pass
        return False
    except Exception as exc:
        print(f"[{stamp()}] State publication deferred: {type(exc).__name__}", flush=True)
        return False
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


BELOW_NORMAL_PRIORITY_CLASS = getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000) if os.name == "nt" else 0
CREATE_NO_WINDOW = (subprocess.CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS) if os.name == "nt" else 0
DAEMON_CREATIONFLAGS = CREATE_NO_WINDOW


def port_up(port: int) -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def alive(kind: str, key: Any) -> bool:
    """Check liveness by kind ('port' or 'proc') and key (port integer or process pattern string)."""
    if kind == "port":
        return port_up(int(key))
    elif kind == "proc":
        return proc_running(str(key))
    return False


def spawn(name, cmd, cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL):
    """Spawn a managed child process with clean process group flags."""
    flags = CREATE_NO_WINDOW
    return subprocess.Popen(
        cmd, cwd=str(cwd), creationflags=flags, stdout=stdout, stderr=stderr
    )


def probe(url: str | None, timeout: float = 1.5):
    if not url or not url.startswith("http"):
        return {"ready": False, "error": "NoHttpUrl"}
    try:
        response = requests.get(url, timeout=(0.5, timeout))
        return {"ready": response.status_code == 200, "http_status": response.status_code}
    except requests.RequestException as exc:
        return {"ready": False, "error": type(exc).__name__}


class ServiceSpec(dict):
    """Service specification supporting both dict access (name, port, cmd, cwd)
    and 5-element tuple unpacking (name, kind, key, cmd, cwd) for full backward compatibility."""

    def __init__(self, name: str, port: int, path: str, cmd: list, cwd: Path | str, match: str = "", allow_external: bool = False):
        kind = "port" if port > 0 else "proc"
        key = port if port > 0 else (match or name)
        resolved_cwd = Path(cwd).resolve()
        super().__init__(
            name=name,
            kind=kind,
            key=key,
            port=port,
            path=path,
            cmd=cmd,
            cwd=resolved_cwd,
            match=match,
            allow_external=allow_external,
        )

    def __iter__(self):
        return iter((self["name"], self["kind"], self["key"], self["cmd"], str(self["cwd"])))

    def __len__(self):
        return 5

    def __getitem__(self, item):
        if isinstance(item, int):
            return (self["name"], self["kind"], self["key"], self["cmd"], str(self["cwd"]))[item]
        return super().__getitem__(item)


def build_services():
    """Build catalog of all 9 core services and optional modules."""
    services = [
        ServiceSpec("Master Operations Command Center", 8770, "/api/health", [PY, "dashboard.py"], ROOT, match="dashboard.py"),
        ServiceSpec("World Monitor Geospatial Radar", 3000, "/", ["cmd.exe", "/c", "npm.cmd", "run", "dev", "--", "--port", "3000", "--host", "127.0.0.1", "--strictPort"], WORLD_MONITOR_ROOT, match="worldmonitor"),
        ServiceSpec("God's Eye View 3D Globe", 4173, "/", ["cmd.exe", "/c", "npm.cmd", "run", "dev", "--", "--port", "4173", "--host", "127.0.0.1"], GODS_EYE_VIEW_ROOT, match="gods-eye-view"),
        ServiceSpec("MQ3 Trading Cockpit", mq3_dashboard_port(), "/api/status", [PY, "run.py", "--demo", "--host", "127.0.0.1", "--port", str(mq3_dashboard_port())], MQ3_ROOT, match="run.py"),
        ServiceSpec("Odysseus AI Brain", 7000, "/api/health", [PY, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "7000"], ROOT / "bots" / "odysseus", match="uvicorn"),
        ServiceSpec("Mobile Companion & Remote Gateway", 8765, "/api/health", [PY, "mobile_control.py"], ROOT, match="mobile_control.py"),
        ServiceSpec("Gods Eye Mobile Viewer", 8766, "/api/health", [PY, "gods_eye_mobile.py"], ROOT, match="gods_eye_mobile.py"),
        ServiceSpec("Global 24/7 Cloud Tunnel", 0, "", [PY, "actions/persistent_tunnel.py"], ROOT, match="persistent_tunnel.py"),
    ]

    ollama = shutil.which("ollama")
    fallback = Path.home() / "AppData/Local/Programs/Ollama/ollama.exe"
    if not ollama and fallback.exists():
        ollama = str(fallback)
    ollama_cmd = [ollama, "serve"] if ollama else ["ollama", "serve"]
    services.insert(0, ServiceSpec("Ollama Local LLM Node", 11434, "/api/tags", ollama_cmd, ROOT, match="ollama"))

    if (ROOT / "wa/node_modules/@whiskeysockets/baileys").exists():
        services.append(ServiceSpec("WhatsApp Gateway Bridge", 3200, "/status", [shutil.which("node") or "node", "jarvis_baileys.js"], ROOT / "wa", match="jarvis_baileys.js"))

    if (ROOT / "bots" / "discord_bot.py").exists():
        services.append(ServiceSpec("Discord Bot Engine", 0, "", [PY, "bots/discord_bot.py"], ROOT, match="discord_bot.py"))

    return services


def acquire_lock():
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(2):
        try:
            with LOCK_FILE.open("x", encoding="utf-8") as handle:
                json.dump(identity(os.getpid()), handle)
            return True
        except FileExistsError:
            try:
                existing = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
                if matching_process(existing):
                    return False
            except (OSError, ValueError):
                try:
                    LOCK_FILE.unlink(missing_ok=True)
                except Exception:
                    pass
                time.sleep(0.2)
                continue
            try:
                LOCK_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    return False


def main():
    if os.path.exists(STOP_FLAG) or STOP_FLAG.exists() or not acquire_lock():
        return
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    records = read_state().get("services", {})
    state = {"root": str(ROOT), "supervisor": identity(os.getpid()), "services": records,
             "mode": "local-research-read-only", "disabled": ["autonomous-trading", "discord", "mission-broadcasts", "whatsapp-group-commands"]}
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = str(ROOT / ".venv")
    env["PATH"] = f"{ROOT / '.venv' / 'Scripts'};{env.get('PATH', '')}"
    env.setdefault("OLLAMA_MODELS", str(ROOT / "data" / "ollama" / "models"))
    env["OLLAMA_HOST"] = "127.0.0.1:11434"
    env["OLLAMA_BASE_URL"] = "http://127.0.0.1:11434"
    env["OLLAMA_NO_CLOUD"] = "1"
    env["ODYSSEUS_INPROCESS_TASKS"] = "0"
    env["ODYSSEUS_INPROCESS_POLLERS"] = "0"
    env.setdefault("JARVIS_ACLED_PAUSED", "1")
    env.setdefault("HF_HOME", str(ROOT / "data" / "huggingface"))
    env.setdefault("OLLAMA_CONTEXT_LENGTH", "4096")
    env.setdefault("OLLAMA_KEEP_ALIVE", "10m")
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("JARVIS_OPENROUTER_ENABLED", "0")
    env.setdefault("JARVIS_GEMINI_ENABLED", "0")
    env.setdefault("JARVIS_WEB_LLM_ENABLED", "0")
    env["JARVIS_WA_GROUP_COMMANDS"] = "0"
    env['MQ3_READ_ONLY'] = '0'
    env['JARVIS_DASHBOARD_BIND'] = os.getenv('JARVIS_DASHBOARD_BIND', '0.0.0.0')
    children = {}
    try:
        while not STOP_FLAG.exists():
            for spec in build_services():
                name = spec["name"]
                rec = records.setdefault(name, {"starts": 0})
                try:
                    disabled = json.loads(OVERRIDES_FILE.read_text(encoding='utf-8')).get('disabled', [])
                except (OSError, ValueError, TypeError):
                    disabled = []
                if name in disabled:
                    rec.update(ready=False, status='disabled-by-owner')
                    continue
                port = spec.get("port", 0)
                url = f"http://127.0.0.1:{port}{spec['path']}" if port > 0 else None
                rec.update({"url": url, "log": str(LOG_DIR / f"{name}.log"), "port": port})
                process = matching_process(rec) if rec.get("owned") else None
                if name in children and children[name].poll() is not None:
                    rec["exit_code"] = children.pop(name).returncode
                if process:
                    if url:
                        observed = probe(rec["url"])
                        rec.pop("error", None)
                        rec.update(observed)
                        rec["status"] = "ready" if observed["ready"] else "starting-or-unhealthy"
                    else:
                        rec.pop("error", None)
                        rec.update({"ready": process.is_running(), "http_status": None})
                        rec["status"] = "ready" if process.is_running() else "starting-or-unhealthy"
                    try:
                        rec["children"] = [identity(p.pid) for p in process.children(recursive=True)]
                    except psutil.Error:
                        pass
                elif port > 0 and port_up(port):
                    # Never adopt or kill an unknown listener simply by its port.
                    observed = probe(rec["url"])
                    rec.update(observed)
                    rec["owned"] = False
                    rec["status"] = "external-ready" if spec.get("allow_external") or observed["ready"] else "port-conflict"
                    if rec["status"] == "port-conflict":
                        rec["ready"] = False
                elif port == 0 and spec.get("match") and proc_running(spec["match"]):
                    rec["owned"] = False
                    rec["ready"] = True
                    rec["status"] = "external-ready"
                elif time.time() >= rec.get("retry_at", 0):
                    if any(matching_process(item) for item in rec.get("children", [])):
                        rec.update(ready=False, status="orphan-child-needs-stop")
                        continue
                    try:
                        with open(rec["log"], "ab", buffering=0) as log:
                            proc = subprocess.Popen(spec["cmd"], cwd=spec["cwd"], env=env,
                                creationflags=DAEMON_CREATIONFLAGS,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                        children[name] = proc
                        rec.update(identity(proc.pid))
                        rec.update(owned=True, ready=False, status="starting", children=[], started_at=stamp())
                        rec["starts"] = rec.get("starts", 0) + 1
                        rec["retry_at"] = time.time() + min(120, 5 * 2 ** min(rec["starts"], 5))
                    except (OSError, psutil.Error) as exc:
                        rec.update(ready=False, status="launch-failed", error=type(exc).__name__, retry_at=time.time() + 60)
                else:
                    rec.update(ready=False, status="restart-backoff")
                rec["checked_at"] = stamp()
            state["checked_at"] = stamp()
            write_state(state)
            time.sleep(3)
    finally:
        state["status"] = "stopped"
        state["checked_at"] = stamp()
        write_state(state)
        LOCK_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
