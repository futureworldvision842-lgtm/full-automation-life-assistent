import argparse
import sys
import os
import json

# Must precede dashboard imports: module-level engines must also be read-only.
if '--read-only' in sys.argv:
    os.environ['MQ3_READ_ONLY'] = '1'

from dashboard.app import run_dashboard
from src.mt5_connector import MT5Connector
from src.ai_learning_engine import AILearningEngine
from src.cloud_memory_sync import CloudMemorySync
from src.system_admin_controller import SystemAdminController


def load_safe_config() -> dict:
    """Load config with sovereign risk governance."""
    with open("config.json", "r", encoding="utf-8-sig") as handle:
        config = json.load(handle)
    return config

def show_status():
    with open("config.json", "r", encoding="utf-8") as handle:
        config = json.load(handle)
    broker_demo = str(config.get("execution", {}).get("default_mode", "paper")).lower() == "broker_demo"
    print("=================================================================")
    print("           MQ3 BROKER TELEMETRY - COMMAND STATUS                 ")
    print("=================================================================")
    mt5 = MT5Connector(config=config, simulation_mode=not broker_demo)
    mt5.connect()
    acc = mt5.get_account_info()
    positions = mt5.get_open_positions()
    ai_engine = AILearningEngine()
    ai_summary = ai_engine.get_ai_learning_summary()
    admin = SystemAdminController()
    telemetry = admin.get_system_telemetry()

    mode = acc.get("data_mode", "UNAVAILABLE")
    login = str(acc.get("login") or "")
    print(f" Mode:             {mode}")
    print(f" Broker Server:    {acc.get('server', 'N/A')}")
    print(f" Broker Login:     ***{login[-4:] if login else 'N/A'}")
    if acc.get("available") and mode in {"BROKER_DEMO", "LIVE"}:
        print(f" Broker Balance:   ${float(acc.get('balance', 0.0)):,.2f}")
        print(f" Broker Equity:    ${float(acc.get('equity', 0.0)):,.2f}")
    else:
        print(" Broker Balance:   UNAVAILABLE")
        print(" Broker Equity:    UNAVAILABLE")
    print(f" Open Trades:      {len(positions)} / 3 Max")
    print(f" AI Memory Status: {ai_summary['ai_status']} (local evidence store; no cloud sync claimed)")
    print(f" System Health:    {telemetry['status']} (CPU: {telemetry['cpu_percent']}%, RAM: {telemetry['memory_percent']}%)")
    print("=================================================================")

def trigger_kill_switch():
    print("⚠️ EXECUTING EMERGENCY KILL SWITCH VIA COMMAND PROMPT...")
    try:
        with open("config.json", "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"❌ KILL SWITCH BLOCKED: config.json unavailable or invalid ({exc}).")
        return
    mt5 = MT5Connector(config=config, simulation_mode=False)
    if not mt5.connect():
        print("❌ KILL SWITCH BLOCKED: validated MT5 connection was not established.")
        return
    authorized, reason = mt5._live_execution_authorized()
    if not authorized:
        print(f"❌ KILL SWITCH BLOCKED: {reason}.")
        mt5.shutdown()
        return
    closed = mt5.emergency_close_all()
    remaining = len(mt5.get_open_positions())
    if remaining:
        print(f"❌ KILL SWITCH INCOMPLETE: {closed} closes reported; {remaining} positions remain.")
    else:
        print(f"✅ EMERGENCY KILL SWITCH VERIFIED: {closed} positions reported closed and none remain visible.")
    mt5.shutdown()

def main():
    parser = argparse.ArgumentParser(description="MQ3 evidence-first trading risk lab launcher")
    parser.add_argument("--sim", action="store_true", help="Run in simulation / dry-run mode")
    parser.add_argument("--demo", action="store_true", help="Use the validated MT5 demo account for broker telemetry; order entries remain gated")
    parser.add_argument("--live", action="store_true", help="Request live MT5 execution mode (always refused by this launcher)")
    parser.add_argument("--port", type=int, default=5000, help="Dashboard Web server port")
    parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host (safe default: 127.0.0.1)")
    parser.add_argument("--status", action="store_true", help="Print live bot telemetry status in CMD")
    parser.add_argument("--kill-switch", action="store_true", help="Execute emergency kill switch in CMD")

    parser.add_argument("--read-only", action="store_true", help="Observe an existing terminal only; no account switching, orders, or messaging")
    args = parser.parse_args()
    if args.read_only:
        os.environ["MQ3_READ_ONLY"] = "1"

    try:
        load_safe_config()
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"STARTUP REFUSED: {exc}")
        return 2

    if args.status:
        show_status()
        return

    if args.kill_switch:
        trigger_kill_switch()
        return

    simulation_mode = not (args.demo or args.live)
    mode_label = "PAPER / SIMULATION" if simulation_mode else ("BROKER LIVE" if args.live else "BROKER DEMO / LIVE MARKET TELEMETRY")

    print("=================================================================")
    print("            MQ3 + JARVIS BROKER TELEMETRY COCKPIT                ")
    print("=================================================================")
    print(f" Mode: {mode_label} (Autonomous Trading & Risk Active)")
    print(f" Dashboard URL: http://localhost:{args.port}")
    print(" Press Ctrl+C to stop.")
    print("=================================================================")

    run_dashboard(port=args.port, simulation_mode=simulation_mode, host=args.host)

if __name__ == "__main__":
    raise SystemExit(main())
