"""Portable owner entry point for the recorded local research fleet."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from bootstrap.supervisor import read_state, matching_process, LOG_DIR
from bootstrap.lifecycle import clear_manual_stop, stop_managed_processes


def start_supervisor(wait=10):
    """Ensure the supervisor runs; it remains the only ownership registry writer."""
    clear_manual_stop()
    if not matching_process(read_state().get("supervisor", {})):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        interpreter = ROOT / ".venv" / "Scripts" / "python.exe"
        with (LOG_DIR / "supervisor.log").open("ab", buffering=0) as log:
            subprocess.Popen([str(interpreter) if interpreter.exists() else sys.executable, "-u",
                              str(ROOT / "bootstrap" / "supervisor.py")],
                             cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    until = time.monotonic() + max(0, min(float(wait), 60))
    while True:
        state = read_state()
        if matching_process(state.get("supervisor", {})):
            return {"ok": True, "running": True, "supervisor": state["supervisor"]}
        if time.monotonic() >= until:
            return {"ok": False, "running": False, "error": "Supervisor did not publish a running identity before timeout."}
        time.sleep(0.25)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "status", "stop"])
    parser.add_argument("--open", action="store_true")
    parser.add_argument("--wait", type=float, default=40)
    parser.add_argument("--mq3", action="store_true", help="Compatibility flag: read-only MQ3 is included in the safe fleet")
    args = parser.parse_args()
    if args.action == "stop":
        result = stop_managed_processes()
    else:
        from bootstrap.master_ecosystem_launcher import start_all_services, get_fleet_status
        result = start_all_services(open_browser=args.open, wait=args.wait) if args.action == "start" else {
            "ok": True, "root": str(ROOT),
            "supervisor_running": bool(matching_process(read_state().get("supervisor", {}))),
            "fleet": get_fleet_status(),
        }
        if args.action == "status" and args.open and result["fleet"].get("dashboard", {}).get("healthy"):
            import webbrowser
            webbrowser.open("http://127.0.0.1:8770")
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
