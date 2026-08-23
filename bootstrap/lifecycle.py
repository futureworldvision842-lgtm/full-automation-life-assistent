"""Owner-controlled lifecycle helpers for the local JARVIS ecosystem.

The stop path is local, explicit and reversible: it raises a manual-stop flag,
finds only processes launched from known JARVIS project folders, and terminates
those processes. It never scans or controls remote machines.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None


ROOT = Path(__file__).resolve().parents[1]
STOP_FLAG = ROOT / "scratch" / "jarvis.stop"
AUDIT_LOG = ROOT / "logs" / "lifecycle.jsonl"
KNOWN_PROJECT_ROOTS = (
    ROOT,
    Path.home() / "jarvis_ts",
    Path(r"E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\backend"),
    Path(r"E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\frontend"),
    Path(r"E:\Muhammad's Work VP automation\full bot\voice-automation my upgradation"),
)
RUNTIME_NAMES = {
    "python.exe", "pythonw.exe", "node.exe", "npm.exe", "npm.cmd",
    "bun.exe", "cmd.exe", "ollama.exe", "clawdbot.exe",
}
MANAGED_MARKERS = (
    "bootstrap\\supervisor.py", "bootstrap/supervisor.py",
    "main.py", "dashboard.py", "mobile_control.py", "server.py", "heartbeat_reporter.py",
    "mission_daemon.py", "jarvis_baileys.js", "jarvis_watchdog",
    "jarvis_supervisor", "clawdbot gateway", "ollama serve",
)


def _normal(value: str | os.PathLike | None) -> str:
    if not value:
        return ""
    try:
        return os.path.normcase(os.path.abspath(os.fspath(value))).rstrip("\\/")
    except Exception:
        return ""


def _under(path: str | os.PathLike | None, roots: Iterable[Path] = KNOWN_PROJECT_ROOTS) -> bool:
    candidate = _normal(path)
    if not candidate:
        return False
    for root in roots:
        base = _normal(root)
        if candidate == base or candidate.startswith(base + os.sep):
            return True
    return False


def process_is_managed(name: str, cmdline: Iterable[str], cwd: str | None) -> bool:
    """Pure process classifier used by the real stop path and unit tests."""
    runtime = str(name or "").lower()
    command = " ".join(str(part) for part in (cmdline or ())).lower()
    if runtime not in RUNTIME_NAMES and not any(runtime.endswith(item) for item in RUNTIME_NAMES):
        return False
    if not _under(cwd):
        return False
    cwd_normal = _normal(cwd)
    root_normal = _normal(ROOT)
    if cwd_normal == root_normal or cwd_normal.startswith(root_normal + os.sep):
        return any(marker.lower() in command for marker in MANAGED_MARKERS)
    # External roots are dedicated JARVIS integrations; npm/bun often hides
    # the script path from CommandLine, so their runtime process is sufficient.
    return True


def request_manual_stop(reason: str = "owner-request") -> Path:
    STOP_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STOP_FLAG.write_text(f"{reason}\n", encoding="utf-8")
    return STOP_FLAG


def clear_manual_stop() -> None:
    try:
        STOP_FLAG.unlink()
    except FileNotFoundError:
        pass


def managed_processes(exclude_pids: Iterable[int] = ()):
    if psutil is None:
        raise RuntimeError("psutil is required for a scoped JARVIS shutdown")
    excluded = {int(pid) for pid in exclude_pids}
    found = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if process.pid in excluded:
                continue
            cwd = process.cwd()
            if process_is_managed(process.info.get("name") or "", process.info.get("cmdline") or (), cwd):
                found.append(process)
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            continue
    return found


def _audit(payload: dict) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {"at": datetime.now(timezone.utc).isoformat(), **payload}
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def stop_managed_processes(reason: str = "owner-request", dry_run: bool = False) -> dict:
    if not dry_run:
        request_manual_stop(reason)
    processes = managed_processes({os.getpid(), os.getppid()})
    by_pid = {process.pid: process for process in processes}
    for process in list(processes):
        try:
            for child in process.children(recursive=True):
                if child.pid not in {os.getpid(), os.getppid()}:
                    by_pid.setdefault(child.pid, child)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    processes = list(by_pid.values())
    details = []
    for process in processes:
        try:
            details.append({
                "pid": process.pid,
                "name": process.name(),
                "cwd": process.cwd(),
                "command": " ".join(process.cmdline())[:500],
            })
        except Exception:
            details.append({"pid": process.pid, "name": "JARVIS process"})

    if not dry_run and processes:
        def depth(item):
            try:
                return len(item.parents())
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return 0
        ordered = sorted(processes, key=depth, reverse=True)
        for process in ordered:
            try:
                process.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        _gone, alive = psutil.wait_procs(processes, timeout=5)
        for process in alive:
            try:
                process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        if alive:
            psutil.wait_procs(alive, timeout=3)

    result = {
        "ok": True,
        "manualStop": not dry_run,
        "dryRun": bool(dry_run),
        "matched": len(details),
        "processes": details,
    }
    _audit({"event": "stop-request", "reason": reason, **result})
    return result
