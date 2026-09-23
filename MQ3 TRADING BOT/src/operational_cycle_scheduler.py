"""
operational_cycle_scheduler.py — 24/7 Background Operational Cycle Scheduler.
Coordinates:
  1. Morning Pre-Market Briefing at 06:30 UTC daily.
  2. Intraday Opportunity Scanning every 5 minutes during London & NY Killzones.
  3. Nightly Retrospective & Cognitive Reflection at 21:30 UTC daily.
"""

import time
import logging
import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine

logger = logging.getLogger("OperationalCycleScheduler")


class OperationalCycleScheduler:
    """
    24/7 Autonomous Background Operational Cycle Scheduler for MetaTrader 5 Fleet.
    """

    def __init__(
        self,
        routine_engine: Optional[DailyInstitutionalRoutineEngine] = None,
        interval_sec: int = 30
    ):
        self.routine_engine = routine_engine if routine_engine else DailyInstitutionalRoutineEngine()
        self.interval_sec = interval_sec
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

        self.last_morning_dispatch: Optional[str] = None
        self.last_nightly_dispatch: Optional[str] = None
        self.last_intraday_scan: Optional[str] = None
        self.execution_log: List[Dict[str, Any]] = []

    def start(self):
        """Starts 24/7 background scheduling loop."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self.run_cycle_loop, daemon=True, name="OperationalSchedulerThread")
        self._thread.start()
        logger.info("OperationalCycleScheduler background thread STARTED.")

    def stop(self):
        """Gracefully halts background scheduling loop."""
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("OperationalCycleScheduler background thread STOPPED.")

    def evaluate_schedule_trigger(self, current_utc_time: datetime) -> Dict[str, bool]:
        """
        Determines active operational cycle triggers for a given UTC timestamp:
          - Morning Briefing: 06:30 UTC daily.
          - Nightly Retrospective: 21:30 UTC daily.
          - Intraday Scanning: London (07:00-10:00), NY AM (12:00-15:00), NY PM (18:00-20:00) every 5 minutes.
        """
        hh_mm = current_utc_time.strftime("%H:%M")
        t = current_utc_time.time()

        trigger_morning = (hh_mm == "06:30")
        trigger_nightly = (hh_mm == "21:30")

        in_london = (7 <= t.hour < 10)
        in_ny_am = (12 <= t.hour < 15)
        in_ny_pm = (18 <= t.hour < 20)
        in_killzone = in_london or in_ny_am or in_ny_pm

        trigger_intraday = in_killzone and (current_utc_time.minute % 5 == 0)

        return {
            "trigger_morning": trigger_morning,
            "trigger_nightly": trigger_nightly,
            "trigger_intraday": trigger_intraday,
            "in_killzone": in_killzone
        }

    def execute_cycle_tick(self, current_utc_time: datetime) -> Dict[str, Any]:
        """
        Executes triggered operational cycles and updates telemetry logs.
        """
        triggers = self.evaluate_schedule_trigger(current_utc_time)
        results: Dict[str, Any] = {"executed": [], "time": current_utc_time.isoformat()}
        today_date = current_utc_time.strftime("%Y-%m-%d")

        # 1. Morning Pre-Market Briefing (06:30 UTC)
        if triggers["trigger_morning"] and self.last_morning_dispatch != today_date:
            try:
                if hasattr(self.routine_engine, "broadcast_morning_briefing"):
                    self.routine_engine.broadcast_morning_briefing()
                elif hasattr(self.routine_engine, "generate_morning_master_briefing"):
                    self.routine_engine.generate_morning_master_briefing()
                self.last_morning_dispatch = today_date
                results["executed"].append("MORNING_BRIEFING")
                self.execution_log.append({"cycle": "MORNING_BRIEFING", "time": current_utc_time.isoformat()})
                logger.info(f"[Scheduler] Dispatched Morning Briefing for {today_date}")
            except Exception as e:
                logger.error(f"[Scheduler Error - Morning Briefing]: {e}")

        # 2. Nightly Retrospective Audit (21:30 UTC)
        if triggers["trigger_nightly"] and self.last_nightly_dispatch != today_date:
            try:
                if hasattr(self.routine_engine, "broadcast_nightly_retrospective"):
                    self.routine_engine.broadcast_nightly_retrospective()
                elif hasattr(self.routine_engine, "generate_nightly_market_retrospective"):
                    self.routine_engine.generate_nightly_market_retrospective()
                self.last_nightly_dispatch = today_date
                results["executed"].append("NIGHTLY_RETROSPECTIVE")
                self.execution_log.append({"cycle": "NIGHTLY_RETROSPECTIVE", "time": current_utc_time.isoformat()})
                logger.info(f"[Scheduler] Dispatched Nightly Retrospective for {today_date}")
            except Exception as e:
                logger.error(f"[Scheduler Error - Nightly Retrospective]: {e}")

        # 3. Intraday Opportunity Scanning (Killzones every 5m)
        if triggers["trigger_intraday"]:
            minute_key = current_utc_time.strftime("%Y-%m-%d %H:%M")
            if self.last_intraday_scan != minute_key:
                try:
                    if hasattr(self.routine_engine, "scan_intraday_opportunities"):
                        scan = self.routine_engine.scan_intraday_opportunities("XAUUSD")
                        if scan.get("triggered") and hasattr(self.routine_engine, "broadcast_intraday_alert"):
                            self.routine_engine.broadcast_intraday_alert(scan.get("signal_card"), "XAUUSD")
                    elif hasattr(self.routine_engine, "generate_intraday_alert"):
                        self.routine_engine.generate_intraday_alert("XAUUSD", "OTE_PULLBACK", "London Open Judas Sweep")
                    self.last_intraday_scan = minute_key
                    results["executed"].append("INTRADAY_ALERT_SCAN")
                    self.execution_log.append({"cycle": "INTRADAY_ALERT_SCAN", "time": current_utc_time.isoformat()})
                except Exception as e:
                    logger.error(f"[Scheduler Error - Intraday Scan]: {e}")

        return results

    def run_cycle_loop(self):
        """Main daemon worker loop."""
        logger.info("OperationalCycleScheduler loop active.")
        while self.is_running:
            try:
                now_utc = datetime.now(timezone.utc)
                self.execute_cycle_tick(now_utc)
            except Exception as e:
                logger.error(f"[Scheduler Loop Exception]: {e}")
            time.sleep(self.interval_sec)
