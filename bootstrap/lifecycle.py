"""Stop only recorded JARVIS process identities; leave unrelated apps alone."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
import psutil

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from bootstrap.supervisor import read_state, matching_process, STOP_FLAG
from platform_runtime import MQ3_ROOT, WORLD_MONITOR_ROOT, GODS_EYE_VIEW_ROOT
AUDIT_LOG = ROOT / "logs" / "lifecycle.jsonl"
KNOWN_PROJECT_ROOTS = (ROOT, WORLD_MONITOR_ROOT, MQ3_ROOT, GODS_EYE_VIEW_ROOT)
CORE_PORTS = (8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678)
MANAGED_MARKERS = (
    "supervisor.py", "dashboard.py", "mobile_control.py", "vite", "uvicorn",
    "ollama serve", "ollama.exe", "run.py", "autonomous_live_daemon.py",
    "discord_bot.py", "gods-eye-view", "worldmonitor", "app.py", "main.py", "terminal.py",
    "server.py", "heartbeat_reporter.py", "mission_daemon.py", "jarvis_baileys.js", "n8n"
)


def _under(path, roots=None) -> bool:
    """Check whether a path is strictly inside or identical to one of the given root directories."""
    if not path:
        return False
    if roots is None:
        roots = KNOWN_PROJECT_ROOTS
    elif isinstance(roots, (str, Path)):
        roots = [roots]
    try:
        norm_path = Path(path).resolve()
    except Exception:
        return False

    for r in roots:
        try:
            norm_r = Path(r).resolve()
            if norm_path == norm_r or norm_r in norm_path.parents:
                return True
        except Exception:
            continue
    return False


def owned_entries(service_names=None, include_supervisor=True):
    """Ownership comes only from recorded PID and creation time pairs."""
    state = read_state()
    entries = [state.get("supervisor", {})] if include_supervisor else []
    for name, rec in state.get("services", {}).items():
        if rec.get("owned") and (service_names is None or name in service_names):
            entries.extend([rec, *rec.get("children", [])])
    unique = {}
    for entry in entries:
        if "pid" in entry and "created" in entry:
            unique[(entry["pid"], entry["created"])] = {"pid": entry["pid"], "created": entry["created"]}
    return list(unique.values())


def _stop_entries(entries):
    details, remaining = [], []
    excluded = {os.getpid(), os.getppid(), 0, 4}
    for entry in entries:
        proc = matching_process(entry)
        if not proc:
            continue
        details.append(dict(entry))
        if proc.pid in excluded:
            remaining.append(proc.pid)
            continue
        try:
            proc.terminate()
        except psutil.NoSuchProcess:
            pass
        except psutil.Error:
            remaining.append(proc.pid)
    for entry in entries:
        proc = matching_process(entry)
        if not proc:
            continue
        if proc.pid in excluded:
            remaining.append(proc.pid)
            continue
        try:
            proc.wait(timeout=2)
        except psutil.TimeoutExpired:
            proc = matching_process(entry)
            if proc:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except psutil.Error:
                    remaining.append(proc.pid)
        except psutil.NoSuchProcess:
            pass
        except psutil.Error:
            remaining.append(proc.pid)
    for entry in entries:
        if matching_process(entry):
            remaining.append(entry["pid"])
    return {"ok": not remaining, "matched": len(details), "processes": details, "remaining": sorted(set(remaining))}


def stop_recorded_services(service_names):
    return _stop_entries(owned_entries(set(service_names), include_supervisor=False))


def kill_process_tree(pid, expected_created=None):
    """Terminate only an exact recorded identity, never an arbitrary PID."""
    for entry in owned_entries():
        if entry.get('pid') == pid and (expected_created is None or entry.get('created') == expected_created):
            if matching_process(entry):
                state = read_state()
                records = [state.get('supervisor', {}), *state.get('services', {}).values()]
                rec = next((r for r in records if r.get('pid') == pid and r.get('created') == entry['created']), entry)
                return _stop_entries([entry, *rec.get('children', [])])['ok']
    return False


def get_pids_on_port(port: int) -> list[int]:
    """Find all PIDs listening on a given port."""
    if port <= 0:
        return []
    pids = set()
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr and conn.laddr.port == port and conn.pid:
                pids.add(conn.pid)
    except Exception:
        pass
    if not pids and os.name == "nt":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "tcp"],
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0].upper() == "TCP":
                    local_addr = parts[1]
                    state = parts[3]
                    pid_str = parts[4]
                    if f":{port}" in local_addr and state.upper() == "LISTENING" and pid_str.isdigit():
                        pids.add(int(pid_str))
        except Exception:
            pass
    return [p for p in pids if p not in (os.getpid(), os.getppid(), 0, 4)]


def process_is_managed(name, cmdline, cwd):
    """Compatibility classifier to identify JARVIS-related processes."""
    if not _under(cwd):
        return False
    try:
        cwd_path = Path(cwd).resolve()
    except Exception:
        cwd_path = None

    name_str = str(name).lower()
    valid_name = name_str in {"python.exe", "pythonw.exe", "node.exe", "cmd.exe", "ollama.exe", "bun.exe"}
    if not valid_name:
        return False

    # Known external project runtime (e.g. world-monitor bun/node server)
    if cwd_path != ROOT and any(cwd_path == r or r in cwd_path.parents for r in KNOWN_PROJECT_ROOTS[1:]) and name_str in {"bun.exe", "node.exe"}:
        return True

    cmd_str = " ".join(cmdline).lower() if isinstance(cmdline, (list, tuple)) else str(cmdline).lower()
    return any(marker in cmd_str for marker in MANAGED_MARKERS)


def request_manual_stop(reason="owner-request"):
    STOP_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STOP_FLAG.write_text(reason + "\n", encoding="utf-8")
    return STOP_FLAG


def clear_manual_stop():
    STOP_FLAG.unlink(missing_ok=True)


def managed_processes(exclude_pids=()):
    excluded = {os.getpid(), os.getppid(), 0, 4, *exclude_pids}
    return [proc for entry in owned_entries()
            if (proc := matching_process(entry)) and proc.pid not in excluded]


def free_ports(ports=CORE_PORTS):
    """Compatibility helper: only recorded owners can be stopped."""
    freed = []
    for port in ports:
        for pid in get_pids_on_port(port):
            if kill_process_tree(pid) and pid not in get_pids_on_port(port):
                freed.append({'port': port, 'pid': pid})
    return freed


def stop_managed_processes(reason="owner-request", dry_run=False):
    entries = owned_entries()
    if dry_run:
        details = [entry for entry in entries if matching_process(entry)]
        return {"ok": True, "manualStop": False, "dryRun": True, "matched": len(details),
                "processes": details, "remaining": [], "freedPorts": []}
    request_manual_stop(reason)
    # Stop the registry writer first so no new children can be created.
    supervisor = read_state().get("supervisor", {})
    if matching_process(supervisor):
        _stop_entries([supervisor])
    recorded = {(entry["pid"], entry["created"]): entry for entry in [*entries, *owned_entries()]}
    result = _stop_entries(list(recorded.values()))
    result.update(manualStop=True, dryRun=False, freedPorts=[])
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "event": "stop-request",
                                 "reason": reason, **result}) + "\n")
    return result
