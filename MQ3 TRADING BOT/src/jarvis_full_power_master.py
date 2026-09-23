"""
JARVIS MASTER ULTIMATE FULL POWER ENGINE — V7
============================================================
Full system access including:
  • Administrator system privileges & self-healing
  • Live desktop screen vision (PIL.ImageGrab)
  • PyAutoGUI HID mouse & keyboard automation
  • Voice channel monitoring (Whisper-style local STT)
  • Dynamic post-trade SL/TP adaptation
  • MT5 live trading oversight
  • Multi-tier cloud memory (Firebase + MongoDB + SQLite)
  • OpenHuman cognitive: Subconscious Reflection + Memory Tree + SuperContext
  • AI-Trader: Signal Quality Scoring + 3-Bot Consensus + Market Regime
  • Multi-Broker IBKR Bridge replication
  • World Monitor geopolitical RSS feed
  • Fincept Terminal quant intel
  • WhatsApp real-time alerts
============================================================
"""

import os
import sys
import time
import json
import logging
import datetime
import threading
import subprocess
from typing import Dict, Any, List, Optional

# ── Core System Control ───────────────────────────────────────────────────────
from src.system_admin_controller import SystemAdminController
from src.system_vision_control import SystemVisionControl
from src.jarvis_agent_intel import JarvisAgentIntel
from src.cloud_memory_sync import CloudMemorySync
from src.world_monitor_feed import WorldMonitorFeed
from src.whatsapp_notifier import WhatsAppNotifier
from src.mt5_connector import MT5Connector

# ── Trading Intelligence ──────────────────────────────────────────────────────
from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.ai_learning_engine import AILearningEngine
from src.fincept_terminal_intel import FinceptTerminalIntel
from src.market_satellite_radar import MarketSatelliteRadar
from src.predictive_weather_engine import PredictiveWeatherEngine

# ── New Repo Integrations ─────────────────────────────────────────────────────
from src.ai_trader_intel import SignalQualityScorer, MultiAgentConsensusVoter, FreeMarketDataFetcher
from src.openhuman_cognitive_engine import SubconsciousReflectionEngine, MemoryTreeManager, SuperContextBuilder
from src.multi_broker_bridge import IBKRBridgeConnector, TradeReplicator

logger = logging.getLogger(__name__)


class JarvisFullPowerMaster:
    """
    JARVIS MASTER ULTIMATE FULL SYSTEM CONTROL ENGINE V7.

    Single unified controller for:
    • Complete system administration authority (CPU, RAM, process healing)
    • Desktop vision capture + PyAutoGUI mouse/keyboard HID automation
    • Live MT5 trade oversight + dynamic SL/TP adaptation
    • OpenHuman subconscious background reflection loop
    • AI-Trader 3-bot consensus + signal quality gate
    • Market satellite radar + weather predictive engine
    • Multi-broker bridge (IBKR position replication)
    • Fincept Terminal quantitative intelligence
    • World Monitor geopolitical risk feed
    • WhatsApp real-time trade + intelligence alerts
    """

    VERSION = "JARVIS-MQ3-SAFE-ORCHESTRATOR-V8"

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.active = True
        self._heartbeat_count = 0

        with open(config_path) as f:
            self.config = json.load(f)

        jarvis_cfg = self.config.get("jarvis_master", {})
        execution_cfg = self.config.get("execution", {})
        self.system_control_active = bool(jarvis_cfg.get("system_control_active", False))
        self.screen_vision_active = bool(jarvis_cfg.get("screen_vision_active", False))
        self.broker_telemetry_active = bool(jarvis_cfg.get("broker_telemetry_active", False))
        self.position_management_active = bool(jarvis_cfg.get("position_management_active", False))
        self.unattended_broadcasts_enabled = bool(
            execution_cfg.get("enable_unattended_routine_broadcasts", False)
        )

        # ── Layer 1: System Authority ─────────────────────────────────────────
        self.admin = SystemAdminController()
        self.vision = SystemVisionControl()

        # ── Layer 2: MT5 & Trading Core ───────────────────────────────────────
        broker_demo_mode = (
            self.broker_telemetry_active
            and str(execution_cfg.get("default_mode", "paper")).lower() == "broker_demo"
            and bool(execution_cfg.get("demo_telemetry_enabled", False))
        )
        self.mt5 = MT5Connector(self.config, simulation_mode=not broker_demo_mode)
        self.risk_manager = RiskManager(self.config)
        self.funding_pips = FundingPipsExpert(self.config)
        self.analyzer = MarketAnalyzer(self.config)
        self.strategy = StrategyEngine(self.config, ai_engine=AILearningEngine())
        self.ai_engine = AILearningEngine()

        # ── Layer 3: Intelligence Modules ─────────────────────────────────────
        self.jarvis_intel = JarvisAgentIntel(config_path=config_path)
        self.fincept = FinceptTerminalIntel()
        self.radar = MarketSatelliteRadar()
        self.weather = PredictiveWeatherEngine()

        # ── Layer 4: Repository Integrations ──────────────────────────────────
        self.signal_scorer = SignalQualityScorer()
        self.consensus_voter = MultiAgentConsensusVoter()
        self.market_data = FreeMarketDataFetcher()
        self.memory_tree = MemoryTreeManager()
        self.subconscious = SubconsciousReflectionEngine()
        self.super_context = SuperContextBuilder(memory_tree=self.memory_tree, reflection=self.subconscious)
        self.ibkr_bridge = IBKRBridgeConnector()
        self.trade_replicator = TradeReplicator(bridge=self.ibkr_bridge)

        # ── Layer 5: Master AI & Multi-Source Intelligence ───────────────────
        from src.higgsfield_vision_engine import HiggsfieldVisionEngine
        from src.public_apis_catalog_engine import PublicAPIsCatalogEngine
        from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine

        self.higgsfield = HiggsfieldVisionEngine(config_path=config_path)
        self.public_apis = PublicAPIsCatalogEngine()
        self.world_monitor_intel = WorldMonitorIntelligenceEngine()

        # ── Layer 6: Communications & Memory ─────────────────────────────────
        self.cloud_mem = CloudMemorySync()
        self.world_feed = WorldMonitorFeed()
        self.whatsapp = WhatsAppNotifier(config_path=config_path)

        # ── Internal State ────────────────────────────────────────────────────
        self._trade_history: List[Dict] = []
        self._alert_log: List[str] = []

        self._banner()

    def _banner(self):
        lines = [
            "=" * 66,
            f"  {self.VERSION}",
            "  BROKER-DEMO TELEMETRY ORCHESTRATION — REAL-MONEY EXECUTION NOT AUTHORIZED",
            "=" * 66,
            "  SYSTEM CAPABILITY / CONNECTION STATUS:",
            "  [ON] Local health telemetry & non-destructive self-checks",
            f"  [{'ON' if self.screen_vision_active else 'OFF'}] Desktop Vision (explicit config flag)",
            f"  [{'ON' if self.system_control_active else 'OFF'}] Mouse/keyboard HID (manual methods only)",
            f"  [{'BROKER DEMO' if not self.mt5.simulation_mode else 'PAPER'}] MT5 telemetry; order entry gates remain locked",
            f"  [{'ON' if self.position_management_active else 'OFF'}] Automatic position mutation",
            "  [LOCAL] OpenHuman-style reflection + local memory tree",
            "  [RESEARCH] 3-bot heuristic consensus; cannot authorize orders",
            "  [RESEARCH] Satellite/weather model; execution multiplier forced to 0",
            "  [MODULE] Fincept/Freqtrade-style local filters; no external terminal session claimed",
            f"  [{'CONNECTED' if self.ibkr_bridge.is_connected else 'NOT CONNECTED'}] Optional IBKR bridge; replication inactive",
            f"  [{'REMOTE AUTH' if self.higgsfield.api_authenticated else 'LOCAL ONLY'}] Candlestick geometry; no remote Higgsfield inference claimed",
            f"  [CATALOG] {self.public_apis.total_apis_indexed} API entries indexed; each feed must verify independently",
            "  [RESEARCH/DEGRADED] World Monitor module; unsourced defaults cannot drive trades",
            f"  [{'ON' if self.unattended_broadcasts_enabled else 'OFF'}] Unattended WhatsApp broadcasts",
            "=" * 66,
        ]
        for line in lines:
            logger.info(line)
            print(line)

    # =========================================================================
    # PUBLIC: Full System Diagnostic
    # =========================================================================

    def run_system_diagnostic(self) -> Dict[str, Any]:
        """Deep system health scan: admin telemetry, vision, memory, world feed."""
        telemetry = self.admin.get_system_telemetry()
        screen = self.vision.capture_screen("jarvis_diagnostic.png") if self.screen_vision_active else None
        world = self.world_feed.fetch_live_world_feed()
        voice = self.vision.listen_voice_command() if self.screen_vision_active else None
        regime = self.market_data.get_market_regime()
        briefing = self.subconscious.generate_morning_briefing()

        diag = {
            "version": self.VERSION,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system_telemetry": telemetry,
            "vision_captured": screen is not None,
            "voice_channel": voice,
            "world_news_count": len(world["news"]),
            "market_regime": regime,
            "session_briefing": briefing,
            "memory_lessons": sum(len(v) for v in self.memory_tree.tree.values()),
            "ibkr_connected": self.ibkr_bridge.is_connected,
        }

        logger.info(
            f"[JARVIS DIAG] CPU:{telemetry['cpu_percent']}% RAM:{telemetry['memory_percent']}% "
            f"Vision:{'OK' if screen else 'FAIL'} Regime:{regime.get('regime','?')} "
            f"News:{len(world['news'])} Lessons:{diag['memory_lessons']}"
        )
        return diag

    # =========================================================================
    # PUBLIC: Full Jarvis Run Loop (threaded heartbeat + trade watch)
    # =========================================================================

    def run_forever(self, poll_interval: int = 20):
        """
        Main Jarvis loop running continuously with full system authority.
        Every tick:
          1. Admin self-heal
          2. MT5 connection check
          3. Open position inspection & SL/TP adaptation
          4. Market regime refresh
          5. Subconscious goal tracking
          6. Screen vision snapshot
          7. World feed scan
          8. WhatsApp heartbeat (every 10 ticks)
        """
        logger.info(f"[JARVIS] run_forever() started (poll={poll_interval}s).")
        self.whatsapp.start_qr_linking_async()

        if not self.mt5.connect():
            logger.warning("[JARVIS] MT5 connection failed — continuing in monitoring mode.")

        acc = self.mt5.get_account_info()
        self.risk_manager.update_daily_baseline(acc["balance"], acc["equity"])
        logger.info(
            f"[JARVIS] MT5 Account #{acc.get('login','SIM')} | "
            f"Balance: ${acc['balance']:.2f} | Equity: ${acc['equity']:.2f}"
        )

        # Startup briefing is logged locally.  It is never sent unless the
        # operator explicitly enables unattended broadcasts in config.json.
        briefing = self.subconscious.generate_morning_briefing()
        regime = self.market_data.get_market_regime()
        startup_msg = (
            f"[JARVIS] {self.VERSION} ONLINE\n"
            f"Balance: ${acc['balance']:.2f} | Equity: ${acc['equity']:.2f}\n"
            f"Market Regime: {regime.get('regime','?')}\n"
            f"Session Ahead: {briefing.get('session_ahead','?')}\n"
            f"Focus: {briefing.get('focus_directive','?')}\n"
            f"BTC: ${regime.get('btc_price',0):,.0f}"
        )
        logger.info("[JARVIS] Startup briefing (local only): %s", startup_msg.replace("\n", " | "))
        self._send_unattended_alert(startup_msg, label="startup briefing")

        while self.active:
            try:
                self._heartbeat_count += 1
                self._tick(acc)

                # Every 10 ticks → Internal telemetry logging + memory compression (no WhatsApp spam)
                if self._heartbeat_count % 10 == 0:
                    logger.debug("[JARVIS] Telemetry tick & memory compression cycle.")
                    self.memory_tree.compress_memory(min_importance=0.2)

                time.sleep(poll_interval)
                # Refresh account info
                acc = self.mt5.get_account_info()

            except KeyboardInterrupt:
                logger.info("[JARVIS] Shutdown requested (KeyboardInterrupt).")
                break
            except Exception as e:
                logger.error(f"[JARVIS] Tick error: {e}", exc_info=True)
                time.sleep(poll_interval)

        logger.info("[JARVIS] Shutdown complete.")

    # =========================================================================
    # PRIVATE: Single Heartbeat Tick
    # =========================================================================

    def _tick(self, acc: Dict[str, Any]):
        tick_num = self._heartbeat_count

        # ── 1. Admin Self-Heal ────────────────────────────────────────────────
        self.admin.self_heal_services()

        # ── 2. Funding Pips Guard ─────────────────────────────────────────────
        self.funding_pips.update_daily_watermark(acc["balance"], acc["equity"])
        allowed, reason = self.funding_pips.can_trade(acc["balance"], acc["equity"])
        if not allowed:
            logger.warning(f"[JARVIS] Funding Pips Guard: {reason}")

        # ── 3. Goal tracking ─────────────────────────────────────────────────
        goals = self.subconscious.update_trading_goals(acc["equity"], acc["balance"])
        if "STOP" in goals.get("recommendation", ""):
            logger.warning(f"[JARVIS] ⚠️ {goals['recommendation']}")
            self._send_unattended_alert(
                f"⚠️ JARVIS ALERT: {goals['recommendation']}",
                label="risk guard alert",
            )

        # ── 4. Screen Vision Capture ──────────────────────────────────────────
        if self.screen_vision_active and tick_num % 3 == 0:
            self.vision.capture_screen(f"jarvis_tick_{tick_num % 10}.png")

        # ── 5. World Geopolitical Feed ────────────────────────────────────────
        if tick_num % 5 == 0:
            world = self.world_feed.fetch_live_world_feed()
            risk = world.get("risk_score", 0)
            if risk > 7:
                msg = f"🌍 JARVIS GEOPOLITICAL ALERT: Risk Score {risk}/10 — {len(world['news'])} events detected!"
                logger.warning(msg)
                self._send_unattended_alert(msg, label="geopolitical alert")

        # ── 6. Open Position Inspection & Adaptive SL/TP ─────────────────────
        positions = self.mt5.get_open_positions()
        for p in positions:
            self._inspect_and_adapt_position(p)

        # ── 7. Market Regime & Subconscious Reflection ────────────────────────
        if tick_num % 4 == 0:
            regime = self.market_data.get_market_regime()
            logger.info(
                f"[JARVIS] Tick #{tick_num} | Regime:{regime.get('regime','?')} "
                f"BTC:${regime.get('btc_price',0):,.0f} "
                f"Positions:{len(positions)} Equity:${acc['equity']:.2f}"
            )

    # =========================================================================
    # PRIVATE: Inspect & Adapt Open Position
    # =========================================================================

    def _inspect_and_adapt_position(self, position: Dict[str, Any]):
        """Full Jarvis inspection of a live trade with adaptive SL/TP."""
        symbol = position.get("symbol", "?")
        ticket = position.get("ticket", 0)

        try:
            df_trend = self.mt5.get_historical_candles(
                symbol, self.config["timeframes"]["trend_tf"], count=50
            )
            df_entry = self.mt5.get_historical_candles(
                symbol, self.config["timeframes"]["entry_tf"], count=50
            )
            if df_trend.empty or df_entry.empty:
                return

            analysis = self.analyzer.analyze_symbol(symbol, df_trend, df_entry)

            # Jarvis visual inspection + dynamic SL/TP
            insp = self.jarvis_intel.inspect_live_trade(position, analysis)
            if insp.get("adjusted"):
                if self.position_management_active:
                    changed = self.mt5.modify_position(ticket, insp["new_sl"], insp["new_tp"])
                    if changed:
                        alert = (
                            f"🔧 JARVIS ADAPTED [{symbol} #{ticket}]\n"
                            f"Reason: {insp['reason']}\n"
                            f"New SL: {insp['new_sl']:.5f}"
                        )
                        logger.info(f"[JARVIS] {alert}")
                        self._send_unattended_alert(alert, label="position adaptation")
                else:
                    logger.info(
                        "[JARVIS] Read-only adaptation suggestion for %s #%s retained locally; position mutation is disabled.",
                        symbol,
                        ticket,
                    )

            # Strict Breakeven shift at full 1:1 R:R
            open_price = position.get("price_open", 0)
            curr_price = position.get("price_current", 0)
            sl = position.get("sl", 0)
            tp = position.get("tp", 0)
            p_type = position.get("type", "BUY")
            original_risk_dist = abs(tp - open_price) / 2.0  # 1R distance
            profit_dist = (curr_price - open_price) if p_type == "BUY" else (open_price - curr_price)
            if self.position_management_active and profit_dist >= original_risk_dist:
                is_sl_behind_entry = (sl < open_price) if p_type == "BUY" else (sl > open_price)
                if is_sl_behind_entry:
                    lock_buffer = 0.05 * original_risk_dist
                    new_sl = (open_price + lock_buffer) if p_type == "BUY" else (open_price - lock_buffer)
                    self.mt5.modify_position(ticket, new_sl, tp)
                    logger.info(f"[JARVIS 1:1 Breakeven] {symbol} #{ticket}: 1R achieved (+{profit_dist:.2f}) → SL locked at {new_sl:.5f}")

        except Exception as e:
            logger.warning(f"[JARVIS] Position inspection error for {symbol} #{ticket}: {e}")

    # =========================================================================
    # PRIVATE: WhatsApp Heartbeat Intelligence Report
    # =========================================================================

    def _send_heartbeat_report(self, acc: Dict[str, Any]):
        """Sends a full intelligence report to WhatsApp every 10 ticks."""
        try:
            regime = self.market_data.get_market_regime()
            telemetry = self.admin.get_system_telemetry()
            positions = self.mt5.get_open_positions()
            goals = self.subconscious.update_trading_goals(acc["equity"], acc["balance"])
            lessons = sum(len(v) for v in self.memory_tree.tree.values())
            world = self.world_feed.fetch_live_world_feed()

            report = (
                f"[JARVIS REPORT]\n"
                f"========================\n"
                f"{self.VERSION}\n"
                f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Balance: ${acc['balance']:.2f}\n"
                f"Equity:  ${acc['equity']:.2f}\n"
                f"PnL:     ${goals.get('pnl', 0):.2f} ({goals.get('pnl_pct', 0):+.2f}%)\n"
                f"Status:  {goals.get('recommendation','?')}\n\n"
                f"Regime:  {regime.get('regime','?')}\n"
                f"BTC:     ${regime.get('btc_price',0):,.0f}\n"
                f"News:    {len(world.get('news',[]))} events\n\n"
                f"Positions: {len(positions)} open\n"
                f"Memory:  {lessons} lessons stored\n"
                f"CPU:     {telemetry.get('cpu_percent',0)}%\n"
                f"RAM:     {telemetry.get('memory_percent',0)}%\n"
                f"========================"
            )
            self._send_unattended_alert(report, label="heartbeat intelligence report")
        except Exception as e:
            logger.warning(f"[JARVIS] Heartbeat report failed: {e}")

    # =========================================================================
    # PUBLIC: Manual Controls (for keyboard/command invocation)
    # =========================================================================

    def _send_unattended_alert(self, message: str, *, label: str) -> bool:
        """Send only when the operator explicitly enabled unattended broadcasts."""
        if not self.unattended_broadcasts_enabled:
            logger.info("[JARVIS] %s retained locally; unattended WhatsApp is disabled.", label)
            return False
        confirmed = self.whatsapp.send_message(message)
        logger.info("[JARVIS] %s delivery confirmed=%s", label, confirmed)
        return confirmed

    def emergency_close_all(self):
        """Emergency close all open positions."""
        logger.warning("[JARVIS] ⛔ EMERGENCY CLOSE ALL POSITIONS TRIGGERED!")
        self.mt5.emergency_close_all()
        self.whatsapp.send_message("⛔ JARVIS: EMERGENCY CLOSE ALL POSITIONS EXECUTED!")

    def take_screenshot(self, filename: str = "manual_screenshot.png") -> Optional[str]:
        """Manually capture a desktop screenshot."""
        if not self.screen_vision_active:
            raise PermissionError("Jarvis screen capture is disabled in config.json")
        return self.vision.capture_screen(filename)

    def move_mouse(self, x: int, y: int):
        """Move mouse to screen coordinates."""
        if not self.system_control_active:
            raise PermissionError("Jarvis mouse control is disabled in config.json")
        self.vision.move_and_click(x, y, click=False)

    def click_at(self, x: int, y: int):
        """Click at screen coordinates."""
        if not self.system_control_active:
            raise PermissionError("Jarvis mouse control is disabled in config.json")
        self.vision.move_and_click(x, y, click=True)

    def press_key(self, keys: str):
        """Send keyboard shortcut."""
        if not self.system_control_active:
            raise PermissionError("Jarvis keyboard control is disabled in config.json")
        self.vision.send_keyboard_shortcut(keys)

    def shutdown(self):
        """Gracefully shutdown Jarvis."""
        self.active = False
        self.mt5.shutdown()
        logger.info("[JARVIS] Graceful shutdown complete.")
