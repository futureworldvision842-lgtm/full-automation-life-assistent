"""
jarvis_agent_intel.py — Jarvis Hermes Agent Intelligence & Muhammad's Jarvis Master Bridge.
========================================================================================
Integrates the complete capabilities of Muhammad-s-Jarvis into the Trading Bot:
  1. Gold Advisor Skill (live Yahoo spot, macro drivers, institutional levels, trade ideas).
  2. World Monitor Feeds (curated multi-category global intelligence & geopolitical alerts).
  3. System Control & Screen Vision (PIL.ImageGrab, PyAutoGUI mouse/keyboard, process health).
  4. Conversational Voice & WhatsApp Dispatcher Integration.
"""

import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from src.system_vision_control import SystemVisionControl

logger = logging.getLogger("JarvisAgentIntel")


class JarvisAgentIntel:
    """
    Jarvis Hermes Agent Intelligence & Master System Control.
    """

    JARVIS_REPO_PATH = "repos/Muhammad-s-Jarvis"

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.agent_active = True
        self.version = "Jarvis-Master-FullPower-v8"
        self.vision = SystemVisionControl()
        self.repo_dir = Path(self.JARVIS_REPO_PATH)

        self._ensure_paths()
        logger.info(f"Jarvis Master Intelligence Initialized ({self.version} | Repo: {self.repo_dir}).")

    def _ensure_paths(self):
        """Ensures Muhammad-s-Jarvis directory is in Python path for direct skill execution."""
        repo_abs = str(self.repo_dir.resolve())
        if os.path.exists(repo_abs) and repo_abs not in sys.path:
            sys.path.insert(0, repo_abs)

    _cached_briefing: Optional[Dict[str, Any]] = None

    def get_gold_advisor_briefing(self, send_whatsapp: bool = False, whatsapp_to: Optional[str] = None, fast_mode: bool = False) -> Dict[str, Any]:
        """
        Executes Muhammad's Jarvis Gold Advisor Skill:
        Fetches live XAU/USD data, recent news, and generates an institutional briefing.
        Supports fast_mode for instant <50ms WhatsApp command SLA.
        """
        now_str = datetime.datetime.now().strftime("%a %d %b, %H:%M")
        fallback_msg = (
            f"🥇 GOLD (XAU/USD) DATA UNAVAILABLE — {now_str}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Status: DEGRADED — no verified current market feed was returned.\n"
            f"• Bias / levels / targets: WITHHELD (unverified data).\n"
            f"• Action: Do not open a trade from this fallback message.\n"
            f"⚠ Informational only — system-status message, not financial advice."
        )
        fallback_resp = {
            "briefing": fallback_msg,
            "source": "SAFE_DEGRADED_FALLBACK",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "success": True,
            "status": "DEGRADED",
            "market_data_available": False,
            "actionable": False,
        }

        if fast_mode:
            return self._cached_briefing or fallback_resp

        try:
            skill_path = self.repo_dir / "skills" / "gold_advisor.py"
            if skill_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("gold_advisor", str(skill_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "run"):
                        params = {"send_whatsapp": send_whatsapp, "whatsapp_to": whatsapp_to}
                        raw_msg = mod.run(params)
                        normalized = str(raw_msg or "").strip()
                        failure_markers = (
                            "couldn't fetch", "could not fetch", "failed to fetch",
                            "unavailable", "error fetching", "no data",
                        )
                        if not normalized or any(marker in normalized.lower() for marker in failure_markers):
                            logger.warning("Gold advisor returned no usable verified market data; using safe degraded response.")
                            self.__class__._cached_briefing = fallback_resp
                            return fallback_resp
                        res = {
                            "briefing": normalized,
                            "source": "Muhammad-s-Jarvis / GoldAdvisor Skill",
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "success": True,
                            "status": "EXTERNAL_RESPONSE_UNVERIFIED",
                            "market_data_available": True,
                            "actionable": False,
                        }
                        self.__class__._cached_briefing = res
                        return res
        except Exception as e:
            logger.warning(f"Error executing external gold_advisor skill: {e}")

        # Institutional native fallback
        self.__class__._cached_briefing = fallback_resp
        return fallback_resp

    def get_world_monitor_headlines(self, category: str = "finance", limit: int = 8) -> List[Dict[str, Any]]:
        """
        Executes Muhammad's Jarvis World Monitor action:
        Pulls live curated RSS headlines across geopolitical, defense, and financial feeds.
        """
        try:
            action_path = self.repo_dir / "actions" / "world_monitor.py"
            if action_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("jarvis_world_monitor", str(action_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "get_headlines"):
                        return mod.get_headlines(category=category, limit=limit)
        except Exception as e:
            logger.warning(f"Error executing external world_monitor action: {e}")

        return [{
            "source": "SYSTEM",
            "title": "Live World Monitor headlines are unavailable; no synthetic news was substituted.",
            "category": category,
            "status": "DEGRADED",
            "data_mode": "UNAVAILABLE",
        }]

    def inspect_live_trade(self, position: Dict[str, Any], market_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inspects an active position live: captures screen image, logs market telemetry.
        Does NOT prematurely move or suffocate SL on normal candle wicks.
        """
        ticket = position.get("ticket")
        symbol = position.get("symbol")
        p_type = position.get("type")
        current_sl = position.get("sl", 0.0)
        current_tp = position.get("tp", 0.0)

        # 1. Screen Vision Inspection
        screen_file = self.vision.capture_screen(f"trade_{ticket}_inspect.png")

        return {
            "ticket": ticket,
            "symbol": symbol,
            "inspected_at": datetime.datetime.now().strftime("%H:%M:%S"),
            "screen_captured": screen_file is not None,
            "adjusted": False,
            "new_sl": current_sl,
            "new_tp": current_tp,
            "reason": "Maintaining full structural SL for 1:2 R:R target",
            "agent_version": self.version
        }

    def process_market_event(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes Jarvis Agent skills on market events."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[Jarvis Agent] Processed event '{event_type}' for {payload.get('symbol', 'GLOBAL')}")

        return {
            "status": "PROCESSED",
            "agent_version": self.version,
            "timestamp": timestamp,
            "event": event_type,
            "recommendation": "EXECUTE_WITH_FUNDING_PIPS_SHIELD"
        }

    def delegate_to_hermes(self, task: str) -> Dict[str, Any]:
        """
        Delegates an autonomous reasoning or execution task to Nous Research Hermes Agent.
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            skill_path = self.repo_dir / "skills" / "hermes.py"
            if skill_path.exists():
                import importlib.util
                spec = importlib.util.spec_from_file_location("hermes_skill", str(skill_path))
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "run"):
                        res = mod.run({"task": task})
                        return {
                            "success": True,
                            "task": task,
                            "response": res,
                            "agent": "Hermes-NousResearch",
                            "timestamp": timestamp
                        }
        except Exception as e:
            logger.warning(f"Hermes delegation error: {e}")

        return {
            "success": False,
            "task": task,
            "response": "Hermes agent is unavailable; the task was not executed.",
            "agent": "Hermes-Unavailable",
            "status": "DEGRADED",
            "timestamp": timestamp
        }
