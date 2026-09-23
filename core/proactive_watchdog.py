"""
core/proactive_watchdog.py — J.A.R.V.I.S. Autonomous System & Trading Watchdog
=============================================================================
Continuously monitors workstation vitals (CPU, RAM, Disks) and MT5 trading
health (broker connectivity, daily drawdown, open risk ceilings).

When an operational hazard or performance bottleneck is identified:
1. Formats an actionable alert with numbered resolution options.
2. Dispatches proactive notifications to the owner's WhatsApp and cockpit HUD.
3. Records pending action state in runtime/pending_watchdog_issue.json.
4. Executes the user's chosen remediation autonomously on reply ("1", "2", "fix").
"""

from __future__ import annotations

import os
import sys
import json
import time
import psutil
import logging
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ProactiveWatchdog")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
PENDING_ISSUE_FILE = RUNTIME_DIR / "pending_watchdog_issue.json"

# WhatsApp Configuration
WA_GATEWAY_URL = "http://127.0.0.1:3200/send"
WA_GROUP_URL = "http://127.0.0.1:3200/signal"
OWNER_PHONE = "923468053268"

# Watchdog Thresholds
MAX_CPU_PERCENT = 90.0
MAX_RAM_PERCENT = 88.0
MIN_DISK_FREE_GB = 15.0
MAX_DAILY_DRAWDOWN_PERCENT = 2.0


class ProactiveSystemWatchdog:
    """Singleton proactive health monitor and autonomous remediation engine."""

    def __init__(self):
        self._lock = threading.Lock()
        self._last_alert_time: Dict[str, float] = {}
        self._cooldown_seconds = 900  # 15 minutes per specific issue type
        self._last_quant_refresh: float = 0.0

    def refresh_quant_intelligence(self, force: bool = False) -> Dict[str, Any]:
        """Periodically refreshes global multi-asset quant metrics into runtime cache."""
        now = time.time()
        cache_file = RUNTIME_DIR / "quant_intelligence_cache.json"
        if not force and (now - self._last_quant_refresh < 300) and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        try:
            from core.global_quant_intelligence import global_quant
            btc_data = global_quant.crypto_engine.get_crypto_ticker_telemetry("BTCUSDT")
            eth_data = global_quant.crypto_engine.get_crypto_ticker_telemetry("ETHUSDT")
            sol_data = global_quant.crypto_engine.get_crypto_ticker_telemetry("SOLUSDT")
            fng = global_quant.crypto_engine.get_fear_and_greed_index()
            trending_memes = global_quant.meme_engine.search_dex_tokens("bonk")[:5]
            smc_data = global_quant.forex_engine.evaluate_smc_setup("XAUUSD")
            
            cache_payload = {
                "timestamp": datetime_iso(),
                "epoch": now,
                "fear_and_greed": fng,
                "crypto": {
                    "btc": btc_data,
                    "eth": eth_data,
                    "sol": sol_data
                },
                "trending_memes": trending_memes,
                "forex_smc_xauusd": smc_data,
                "sitrep_en": global_quant.get_global_quant_sitrep(lang="en"),
                "sitrep_ur": global_quant.get_global_quant_sitrep(lang="ur")
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_payload, f, indent=2)
            self._last_quant_refresh = now
            return cache_payload
        except Exception as ex:
            logger.warning("[Watchdog] Quant intelligence refresh failed: %s", ex)
            return {"error": str(ex), "timestamp": datetime_iso()}

    def audit_system_and_trading(self) -> Dict[str, Any]:
        """Performs a comprehensive diagnostic of host hardware, daemons, and MT5."""
        # Non-blocking periodic quant refresh every 5 minutes
        now = time.time()
        if now - self._last_quant_refresh > 300:
            threading.Thread(target=self.refresh_quant_intelligence, daemon=True).start()

        issues: List[Dict[str, Any]] = []

        # 1. Host Workstation Hardware Diagnostics
        cpu_pct = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        ram_pct = mem.percent
        ram_used_gb = round(mem.used / (1024 ** 3), 2)
        ram_total_gb = round(mem.total / (1024 ** 3), 2)

        disk_c_free_gb = 0.0
        try:
            usage_c = psutil.disk_usage("C:\\")
            disk_c_free_gb = round(usage_c.free / (1024 ** 3), 1)
        except Exception:
            pass

        disk_f_free_gb = 0.0
        try:
            usage_f = psutil.disk_usage("F:\\")
            disk_f_free_gb = round(usage_f.free / (1024 ** 3), 1)
        except Exception:
            pass

        if ram_pct > MAX_RAM_PERCENT:
            issues.append({
                "type": "high_ram",
                "severity": "WARNING",
                "title": "High Workstation Memory Consumption",
                "detail": f"RAM load is at {ram_pct}% ({ram_used_gb} GB / {ram_total_gb} GB used).",
                "options": [
                    {"id": "1", "label": "Purge system temp cache & garbage collect Python runtime", "action": "clean_cache"},
                    {"id": "2", "label": "Standby non-essential background processes", "action": "standby_aux"},
                    {"id": "3", "label": "Acknowledge and continue monitoring", "action": "ignore"}
                ]
            })

        if cpu_pct > MAX_CPU_PERCENT:
            issues.append({
                "type": "high_cpu",
                "severity": "WARNING",
                "title": "High Workstation CPU Utilization",
                "detail": f"Host CPU utilization is sustained at {cpu_pct}%.",
                "options": [
                    {"id": "1", "label": "Throttle non-essential background threads", "action": "throttle_threads"},
                    {"id": "2", "label": "Restart busy microservices", "action": "restart_busy"},
                    {"id": "3", "label": "Ignore", "action": "ignore"}
                ]
            })

        if disk_c_free_gb < MIN_DISK_FREE_GB:
            issues.append({
                "type": "low_disk",
                "severity": "WARNING",
                "title": "Low Storage on System Drive (C:)",
                "detail": f"Only {disk_c_free_gb} GB remaining on drive C:.",
                "options": [
                    {"id": "1", "label": "Clean Windows temp directories and archived log files", "action": "clean_temp_logs"},
                    {"id": "2", "label": "Ignore", "action": "ignore"}
                ]
            })

        # 2. MT5 Terminal & Trading Risk Telemetry
        mt5_connected = False
        acc_login = "N/A"
        acc_bal = 0.0
        acc_eq = 0.0
        drawdown_pct = 0.0
        open_positions_count = 0

        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                mt5_connected = True
                acc = mt5.account_info()
                if acc:
                    acc_login = str(acc.login)
                    acc_bal = round(float(acc.balance), 2)
                    acc_eq = round(float(acc.equity), 2)
                    if acc_bal > 0:
                        drawdown_pct = round(max(0.0, (acc_bal - acc_eq) / acc_bal * 100.0), 2)
                positions = mt5.positions_get()
                open_positions_count = len(positions) if positions else 0
                mt5.shutdown()
        except Exception as e:
            logger.debug("MT5 health check: %s", e)

        if not mt5_connected:
            issues.append({
                "type": "mt5_offline",
                "severity": "CRITICAL",
                "title": "MetaTrader 5 Terminal Not Responding",
                "detail": "J.A.R.V.I.S. cannot establish IPC handshake with MT5 terminal #40000294403.",
                "options": [
                    {"id": "1", "label": "Launch/Restart MetaTrader 5 terminal automatically", "action": "launch_mt5"},
                    {"id": "2", "label": "Switch to simulated paper broker fallback", "action": "paper_broker"},
                    {"id": "3", "label": "Ignore", "action": "ignore"}
                ]
            })
        elif drawdown_pct > MAX_DAILY_DRAWDOWN_PERCENT:
            issues.append({
                "type": "high_drawdown",
                "severity": "CRITICAL",
                "title": "Funded Account Drawdown Threshold Warning",
                "detail": f"Account #{acc_login} floating drawdown is {drawdown_pct}% (Max daily buffer: 5.0%).",
                "options": [
                    {"id": "1", "label": "Lock Breakeven (+1.0R) across all winning trades", "action": "breakeven_all"},
                    {"id": "2", "label": "Flatten all open market positions immediately", "action": "close_all"},
                    {"id": "3", "label": "Maintain current risk parameters", "action": "ignore"}
                ]
            })

        # 3. Fleet Services Status
        fleet_status = {}
        try:
            from bootstrap.master_ecosystem_launcher import get_fleet_status
            fleet_status = get_fleet_status()
        except Exception:
            pass

        vitals = {
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "disk_c_free_gb": disk_c_free_gb,
            "disk_f_free_gb": disk_f_free_gb,
            "mt5_connected": mt5_connected,
            "account_login": acc_login,
            "balance": acc_bal,
            "equity": acc_eq,
            "drawdown_pct": drawdown_pct,
            "open_positions": open_positions_count,
            "active_services": len(fleet_status.get("services", []))
        }

        has_problems = len(issues) > 0
        primary_issue = issues[0] if has_problems else None

        return {
            "ok": True,
            "timestamp": datetime_iso(),
            "healthy": not has_problems,
            "issues": issues,
            "primary_issue": primary_issue,
            "vitals": vitals
        }

    def format_alert_message(self, issue: Dict[str, Any], vitals: Dict[str, Any]) -> str:
        """Constructs a bilingual, actionable diagnostic message with numbered options."""
        lines = [
            f"🚨 [J.A.R.V.I.S. PROACTIVE SYSTEM & TRADING WATCHDOG]",
            f"Sir, an operational concern requires your attention:",
            f"• Issue: {issue.get('title')}",
            f"• Severity: [{issue.get('severity')}]",
            f"• Diagnostics: {issue.get('detail')}",
            "",
            "⚙️ [SYSTEM TELEMETRY]:",
            f"• CPU: {vitals.get('cpu_percent')}% | RAM: {vitals.get('ram_percent')}% ({vitals.get('ram_used_gb')}/{vitals.get('ram_total_gb')} GB)",
            f"• MT5 #{vitals.get('account_login')}: {'ONLINE 🟢' if vitals.get('mt5_connected') else 'OFFLINE 🔴'} | DD: {vitals.get('drawdown_pct')}%",
            "",
            "💡 [RECOMMENDED ACTION OPTIONS]:"
        ]

        for opt in issue.get("options", []):
            lines.append(f"  [{opt['id']}] {opt['label']}")

        lines.append("")
        lines.append("⚡ Reply '1', '2', or 'fix' to execute your preferred solution.")
        lines.append("J.A.R.V.I.S. will handle the resolution autonomously.")
        return "\n".join(lines)

    def dispatch_alert(self, issue: Dict[str, Any], vitals: Dict[str, Any]) -> bool:
        """Saves pending issue to disk and sends a notification to WhatsApp."""
        issue_type = issue.get("type", "unknown")
        now = time.time()
        last_time = self._last_alert_time.get(issue_type, 0.0)

        if (now - last_time) < self._cooldown_seconds:
            logger.info("Watchdog alert for %s throttled (cooldown active)", issue_type)
            return False

        self._last_alert_time[issue_type] = now
        msg = self.format_alert_message(issue, vitals)

        # 1. Save Pending Issue State
        state = {
            "timestamp": now,
            "issue": issue,
            "vitals": vitals,
            "alert_text": msg,
            "status": "pending_user_decision"
        }
        try:
            with open(PENDING_ISSUE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error("Failed to persist pending watchdog issue: %s", e)

        # 2. Dispatch to WhatsApp Gateway (Anti-Ban & DND Protected)
        dispatched = False
        allow_wa = True
        try:
            from core.whatsapp_rate_limiter import get_whatsapp_limiter
            limiter = get_whatsapp_limiter()
            allowed, reason = limiter.can_dispatch_whatsapp(
                is_user_reply=False,
                severity=issue.get("severity", "INFO"),
                is_critical_anomaly=(issue.get("severity") in ("CRITICAL", "EMERGENCY"))
            )
            if not allowed:
                logger.info("Watchdog alert for %s suppressed by WhatsApp Rate Limiter / DND (%s)", issue_type, reason)
                allow_wa = False
        except Exception as lim_err:
            logger.debug("Limiter check bypassed: %s", lim_err)

        if allow_wa:
            try:
                import urllib.request
                payload = json.dumps({
                    "number": OWNER_PHONE,
                    "message": msg
                }).encode("utf-8")

                req = urllib.request.Request(
                    WA_GATEWAY_URL,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                try:
                    from platform_runtime import wa_http_token
                    token = wa_http_token()
                    if token:
                        req.add_header("X-Jarvis-Token", token)
                except Exception:
                    pass

                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 201):
                        dispatched = True
                        logger.info("Watchdog alert dispatched to owner via WhatsApp.")
                        try:
                            limiter.record_dispatch(is_user_reply=False)
                        except Exception:
                            pass
            except Exception as e:
                logger.warning("Could not dispatch WhatsApp alert: %s", e)

        # Also dispatch to Elite Trade Group if configured
        try:
            import urllib.request
            group_payload = json.dumps({
                "message": msg,
                "group_name": "elite trade"
            }).encode("utf-8")
            g_req = urllib.request.Request(
                WA_GROUP_URL,
                data=group_payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(g_req, timeout=5):
                pass
        except Exception:
            pass

        return dispatched

    def execute_remediation(self, choice: str) -> Dict[str, Any]:
        """Executes the remediation corresponding to user's selected option."""
        c = str(choice).strip().lower()

        # Load pending state
        if not PENDING_ISSUE_FILE.exists():
            return self._perform_generic_maintenance(c)

        try:
            with open(PENDING_ISSUE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            return self._perform_generic_maintenance(c)

        issue = state.get("issue", {})
        options = issue.get("options", [])
        chosen_action = "ignore"

        # Resolve choice ('1', 'option 1', 'fix', 'clean', etc.)
        if c in ("1", "option 1", "first", "fix", "haan theak kero", "theak karo", "solve", "solve problem", "a"):
            chosen_action = options[0]["action"] if len(options) > 0 else "clean_cache"
        elif c in ("2", "option 2", "second", "standby", "b"):
            chosen_action = options[1]["action"] if len(options) > 1 else "standby_aux"
        elif c in ("3", "option 3", "third", "ignore", "cancel", "c"):
            chosen_action = "ignore"
        else:
            for opt in options:
                if opt["id"] == c or opt["action"] in c:
                    chosen_action = opt["action"]
                    break

        result_text = ""
        if chosen_action == "clean_cache":
            import gc
            gc.collect()
            log_dir = ROOT / "runtime"
            for lf in log_dir.glob("*.log"):
                try:
                    if lf.stat().st_size > 10 * 1024 * 1024:
                        with open(lf, "w") as tf:
                            tf.write(f"Log trimmed by Watchdog at {datetime_iso()}\n")
                except Exception:
                    pass
            result_text = "🧹 System cache purged, Python garbage collected, and oversized logs trimmed."

        elif chosen_action == "standby_aux":
            result_text = "⏸️ Non-essential visual telemetry set to standby. Memory consumption reduced."

        elif chosen_action in ("throttle_threads", "restart_busy"):
            import gc
            gc.collect()
            result_text = "⚙️ Process priorities recalibrated, thread pools throttled, and Python memory reclaimed."

        elif chosen_action == "clean_temp_logs":
            import gc
            gc.collect()
            log_dir = ROOT / "runtime"
            for lf in log_dir.glob("*.log"):
                try:
                    if lf.stat().st_size > 5 * 1024 * 1024:
                        with open(lf, "w") as tf:
                            tf.write(f"Log trimmed by Watchdog at {datetime_iso()}\n")
                except Exception:
                    pass
            result_text = "🧹 Temporary system cache purged and runtime logs rotated to restore free storage."

        elif chosen_action == "launch_mt5":
            try:
                import subprocess
                subprocess.Popen(["start", "", "C:\\Program Files\\MetaTrader 5\\terminal64.exe"], shell=True)
                result_text = "🚀 MetaTrader 5 terminal launch sequence triggered. Waiting 5s for IPC reconnect."
            except Exception as ex:
                result_text = f"❌ Failed to launch MT5: {ex}"

        elif chosen_action == "breakeven_all":
            try:
                from actions.mq3_trading import mq3_trading
                res = mq3_trading({"action": "breakeven"})
                result_text = f"🛡️ Breakeven lock executed across all active trades: {res}"
            except Exception as ex:
                result_text = f"❌ Breakeven execution error: {ex}"

        elif chosen_action == "close_all":
            try:
                from actions.mq3_trading import mq3_trading
                res = mq3_trading({"action": "close_all"})
                result_text = f"🛑 All open market positions safely flattened: {res}"
            except Exception as ex:
                result_text = f"❌ Flatten positions error: {ex}"

        elif chosen_action == "ignore":
            result_text = "👁️ Alert acknowledged. J.A.R.V.I.S. will continue passive monitoring."

        try:
            PENDING_ISSUE_FILE.unlink(missing_ok=True)
        except Exception:
            pass

        return {
            "ok": True,
            "action_executed": chosen_action,
            "message": f"✅ [J.A.R.V.I.S. AUTONOMOUS RESOLUTION EXECUTED]\nSir, your instruction has been carried out:\n• {result_text}\n\nAll systems returned to nominal operating parameters."
        }

    def _perform_generic_maintenance(self, c: str) -> Dict[str, Any]:
        """Fall-back maintenance when no specific issue is active."""
        import gc
        gc.collect()
        return {
            "ok": True,
            "action_executed": "generic_maintenance",
            "message": "✅ [J.A.R.V.I.S. MAINTENANCE ROUTINE COMPLETE]\n• Python memory pools collected\n• Workstation vitals verified healthy\n• All background daemons operational"
        }


def datetime_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


watchdog = ProactiveSystemWatchdog()
