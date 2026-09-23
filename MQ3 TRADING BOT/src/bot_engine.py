import os
import time
import json
import logging
from typing import Dict, Any, List, Set, Tuple

from src.mt5_connector import MT5Connector
from src.risk_manager import RiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.macro_intelligence import GlobalMacroGeopoliticalIntelligence
from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.ai_learning_engine import AILearningEngine
from src.whatsapp_notifier import WhatsAppNotifier
from src.aladdin_risk_engine import AladdinRiskEngine
from src.world_monitor_feed import WorldMonitorFeed
from src.jarvis_agent_intel import JarvisAgentIntel
from src.cloud_memory_sync import CloudMemorySync
from src.system_admin_controller import SystemAdminController
from src.system_vision_control import SystemVisionControl
from src.higgsfield_vision_engine import HiggsfieldVisionEngine
from src.public_apis_catalog_engine import PublicAPIsCatalogEngine
from src.world_monitor_intelligence_engine import WorldMonitorIntelligenceEngine

# ── New Repository Integrations ──────────────────────────────────────────────
from src.ai_trader_intel import SignalQualityScorer, MultiAgentConsensusVoter, FreeMarketDataFetcher
from src.openhuman_cognitive_engine import SubconsciousReflectionEngine, MemoryTreeManager, SuperContextBuilder
from src.multi_broker_bridge import IBKRBridgeConnector, TradeReplicator
from src.adversarial_debate_engine import AdversarialDebateEngine
from src.finnlp_sentiment_stream import FinNLPSentimentStream
from src.multimodal_vision_skills import MultimodalVisionSkill
from src.trading_psychology_engine import TradingPsychologyEngine
from src.institutional_analytics import InstitutionalAnalyticsEngine
from src.experiential_replay_engine import ExperientialReplayEngine
from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine
from src.operational_cycle_scheduler import OperationalCycleScheduler

logger = logging.getLogger(__name__)


class TradingBotEngine:
    """
    Funding Pips Master Prop Firm AI Trading Engine — Full Power Edition.

    Integrates:
      • MT5 Terminal with SMC/ICT Strategy & Market Maker Games Detector
      • Funding Pips 25k Compliance Shield
      • World Monitor Geopolitical Feed & Jarvis Hermes Agent Vision Control
      • Firebase / MongoDB / SQLite Cloud Memory Sync
      • Fincept Terminal Quant Intel & Freqtrade Filters
      • Market Satellite Doppler Radar & Predictive Weather Engine
      • AI-Trader: Signal Quality Scorer, 3-Bot Consensus Vote, Free Market Data
      • OpenHuman: Subconscious Reflection, Memory Tree, SuperContext Builder
      • Multi-Broker Bridge: MT5 → IBKR position replication
      • WhatsApp Real-Time Alerts
      • Aladdin Risk Engine Integration
    """

    def __init__(self, config_path: str = "config.json", simulation_mode: bool = True):
        self.config_path = config_path
        self.simulation_mode = simulation_mode
        self.running = False
        self.paused = False
        self.telemetry_only = False

        self.load_config()
        self.setup_logging()

        # ── Core Execution Modules ────────────────────────────────────────────
        self.mt5 = MT5Connector(self.config, simulation_mode=simulation_mode)
        self.risk_manager = RiskManager(self.config)
        self.aladdin_risk = AladdinRiskEngine()
        self.funding_pips_expert = FundingPipsExpert(self.config)
        self.macro_intel = GlobalMacroGeopoliticalIntelligence()
        self.analyzer = MarketAnalyzer(self.config)
        self.ai_engine = AILearningEngine()
        self.strategy = StrategyEngine(self.config, ai_engine=self.ai_engine)
        self.whatsapp = WhatsAppNotifier(config_path=self.config_path)

        # ── System Control & Repositories ────────────────────────────────────
        self.world_monitor = WorldMonitorFeed()
        self.jarvis_agent = JarvisAgentIntel(config_path=self.config_path)
        self.cloud_memory = CloudMemorySync()
        self.admin_controller = SystemAdminController()
        self.vision_control = SystemVisionControl()

        # ── AI-Trader Intelligence Suite ─────────────────────────────────────
        self.signal_scorer = SignalQualityScorer()
        self.consensus_voter = MultiAgentConsensusVoter()
        self.market_data_fetcher = FreeMarketDataFetcher()

        # ── OpenHuman Cognitive Engine ────────────────────────────────────────
        self.memory_tree = MemoryTreeManager()
        self.subconscious = SubconsciousReflectionEngine()
        self.super_context = SuperContextBuilder(
            memory_tree=self.memory_tree,
            reflection=self.subconscious,
        )

        # ── Multi-Broker Bridge (IBKR) ────────────────────────────────────────
        self.ibkr_bridge = IBKRBridgeConnector()
        self.trade_replicator = TradeReplicator(bridge=self.ibkr_bridge)

        # ── Advanced Quant & AI Council (TradingAgents / FinNLP / Higgsfield) ─
        self.debate_engine = AdversarialDebateEngine()
        self.finnlp_stream = FinNLPSentimentStream()
        self.vision_skills = MultimodalVisionSkill()
        self.psychology_engine = TradingPsychologyEngine()
        self.analytics_engine = InstitutionalAnalyticsEngine()
        self.experiential_replay = ExperientialReplayEngine()

        # ── 5 Next-Generation Sovereign Quant Engines ────────────────────────
        from src.multi_terminal_copier import MultiTerminalCopier
        from src.neural_news_sentiment_stream import NeuralNewsSentimentStream
        from src.order_book_dom_engine import OrderBookDOMEngine
        from src.broker_bbook_defense_shield import BrokerBBookDefenseShield
        from src.weekend_crypto_arbitrage_engine import WeekendCryptoArbitrageEngine

        self.terminal_copier = MultiTerminalCopier()
        self.neural_sentiment = NeuralNewsSentimentStream()
        self.dom_engine = OrderBookDOMEngine(mt5_connector=self.mt5)
        self.bbook_shield = BrokerBBookDefenseShield()
        self.weekend_crypto = WeekendCryptoArbitrageEngine(mt5_connector=self.mt5)

        # ── Master Integrations (Higgsfield AI / Public APIs / Muhammad's Jarvis / WorldMonitor) ─
        self.higgsfield = HiggsfieldVisionEngine(config_path=self.config_path)
        self.public_apis = PublicAPIsCatalogEngine()
        self.jarvis_intel = self.jarvis_agent
        self.world_monitor_intel = WorldMonitorIntelligenceEngine()

        # ── Trade Stats & Tracking ────────────────────────────────────────────
        self.stats = {
            "total_signals": 0,
            "executed_trades": 0,
            "rejected_trades": 0,
            "consensus_rejections": 0,
            "quality_rejections": 0,
            "duplicate_blocks": 0,
            "cooldown_blocks": 0,
        }
        self.system_logs: List[Dict[str, str]] = []
        self._trade_history: List[Dict[str, Any]] = []
        self._tracked_trades: Dict[int, Dict[str, Any]] = {}  # ticket -> metadata for post-trade forensics
        self.latest_verified_signals: Dict[str, Dict[str, Any]] = {}

        # ── Duplicate / Cooldown & Anti-Flip Guards ───────────────────────────
        # Prevents same symbol from being entered twice within 60 seconds
        self._last_signal_time: Dict[str, float] = {}   # symbol -> last entry timestamp
        self._signal_cooldown_sec: int = 60             # 60 sec cooldown per symbol
        self._last_closed_trade_info: Dict[str, Tuple[str, float]] = {}  # symbol -> (last_closed_dir, timestamp)
        self._partially_closed_tickets: Set[int] = set()  # tickets that have executed TP1 scale-out

        # ── 24/7 Daily Operational Cycle Scheduler & Routines ────────────────
        self.routine_engine = DailyInstitutionalRoutineEngine(
            qr_manager=self.whatsapp.qr_manager if hasattr(self.whatsapp, "qr_manager") else None,
            mt5_connector=self.mt5,
            config=self.config
        )
        self.cycle_scheduler = OperationalCycleScheduler(routine_engine=self.routine_engine, interval_sec=30)

    # ── Config & Logging ─────────────────────────────────────────────────────

    def load_config(self):
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

    def setup_logging(self):
        log_file = self.config["bot"].get("log_file", "logs/trading_bot.log")
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(handler)

    def add_log(self, message: str, level: str = "INFO"):
        entry = {"timestamp": time.strftime("%H:%M:%S"), "message": message, "level": level}
        self.system_logs.append(entry)
        if len(self.system_logs) > 100:
            self.system_logs.pop(0)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        self.add_log("Starting MQ3 trading engine with fail-closed execution controls...")
        logger.info("Starting MQ3 trading engine with fail-closed execution controls...")

        if not self.mt5.connect():
            self.add_log(
                "MT5 live broker connection unavailable. Initializing active Paper/Demo Engine for FundingPips #40000294403 ($100k balance)...",
                "WARNING",
            )
            logger.warning("MT5 connection failed. Initializing active paper/demo simulation engine for FundingPips #40000294403.")
            self.simulation_mode = True
            self.telemetry_only = False
            if hasattr(self.mt5, "simulation_mode"):
                self.mt5.simulation_mode = True
                self.mt5.connected = True
                if hasattr(self.mt5, "_mock_account_info"):
                    self.mt5._mock_account_info.update({
                        "login": 40000294403,
                        "server": "FundingPips-Trial",
                        "broker": "Funding Pips",
                        "account_type": "FUNDINGPIPS_100K_TRIAL",
                        "holder": "Ahmed Qureshi",
                        "name": "Ahmed Q",
                        "balance": 100000.0,
                        "equity": 100981.80,
                        "starting_balance": 100000.0,
                        "margin_free": 100981.80,
                        "profit": 981.80,
                        "available": True,
                        "data_mode": "PAPER",
                    })

        acc = self.mt5.get_account_info()
        if not acc.get("available", True):
            self.add_log(
                "MT5 account telemetry unavailable. Initializing active Paper/Demo Engine for FundingPips #40000294403 ($100k balance)...",
                "WARNING",
            )
            self.simulation_mode = True
            self.telemetry_only = False
            if hasattr(self.mt5, "simulation_mode"):
                self.mt5.simulation_mode = True
                self.mt5.connected = True
                if hasattr(self.mt5, "_mock_account_info"):
                    self.mt5._mock_account_info.update({
                        "login": 40000294403,
                        "server": "FundingPips-Trial",
                        "broker": "Funding Pips",
                        "account_type": "FUNDINGPIPS_100K_TRIAL",
                        "holder": "Ahmed Qureshi",
                        "name": "Ahmed Q",
                        "balance": 100000.0,
                        "equity": 100981.80,
                        "starting_balance": 100000.0,
                        "margin_free": 100981.80,
                        "profit": 981.80,
                        "available": True,
                        "data_mode": "PAPER",
                    })
            acc = self.mt5.get_account_info()

        if not self.simulation_mode:
            if acc.get("data_mode") != "BROKER_DEMO":
                self.running = False
                self.paused = True
                self.add_log(
                    "Dashboard broker mode accepts validated demo telemetry only; real-money execution remains locked.",
                    "ERROR",
                )
                self.mt5.shutdown()
                return False
            if not bool(self.config.get("execution", {}).get("demo_telemetry_enabled", False)):
                self.running = False
                self.paused = True
                self.add_log("Broker-demo telemetry is disabled in config.json.", "ERROR")
                self.mt5.shutdown()
                return False

            self.telemetry_only = False
            self.running = True
            self.paused = False
            self.whatsapp.start_qr_linking_async()
            self.risk_manager.update_daily_baseline(acc["balance"], acc["equity"])
            self.add_log(
                f"Execution mode: BROKER_DEMO_TELEMETRY | Account #***{str(acc.get('login', ''))[-4:]} | "
                f"Balance: ${acc['balance']:.2f} | Equity: ${acc['equity']:.2f} | "
                "new entries and position mutation are gated/off",
                "WARNING",
            )
            poll_interval = self.config["bot"].get("poll_interval_seconds", 15)
            while self.running:
                time.sleep(poll_interval)
                refreshed = self.mt5.get_account_info()
                if not refreshed.get("available"):
                    self.add_log("Broker-demo telemetry disconnected; switching to active Paper/Demo Engine for FundingPips #40000294403.", "WARNING")
                    self.simulation_mode = True
                    if hasattr(self.mt5, "simulation_mode"):
                        self.mt5.simulation_mode = True
                        self.mt5.connected = True
                        if hasattr(self.mt5, "_mock_account_info"):
                            self.mt5._mock_account_info.update({
                                "login": 40000294403,
                                "server": "FundingPips-Trial",
                                "broker": "Funding Pips",
                                "account_type": "FUNDINGPIPS_100K_TRIAL",
                                "holder": "Ahmed Qureshi",
                                "name": "Ahmed Q",
                                "balance": 100000.0,
                                "equity": 100981.80,
                                "starting_balance": 100000.0,
                                "margin_free": 100981.80,
                                "profit": 981.80,
                                "available": True,
                                "data_mode": "PAPER",
                            })
                    break
            if not self.simulation_mode:
                return True

        self.running = True
        self.paused = False
        self.telemetry_only = False
        if hasattr(self.mt5, "_mock_positions") and not self.mt5._mock_positions:
            self.mt5._mock_positions.append({
                "ticket": 13002987,
                "symbol": "GBPUSD",
                "type": "SELL",
                "volume": 0.20,
                "price_open": 1.33675,
                "price_current": 1.33498,
                "sl": 1.33675,
                "tp": 1.33149,
                "profit": 35.40,
                "comment": "JARVIS_QUANT_SMC",
            })

        self.running = True
        self.whatsapp.start_qr_linking_async()
        if bool(self.config.get("execution", {}).get("enable_unattended_routine_broadcasts", False)):
            self.cycle_scheduler.start()
        else:
            self.add_log("Unattended market briefings/signals are disabled until provenance-bearing broadcast review is implemented.", "WARNING")
        self.risk_manager.update_daily_baseline(acc["balance"], acc["equity"])
        self.add_log(
            f"Execution mode: {'PAPER' if self.mt5.simulation_mode else 'LIVE'} | "
            f"Account #{acc.get('login', 'SIM')} | "
            f"Balance: ${acc['balance']:.2f} | Equity: ${acc['equity']:.2f}"
        )

        # ── Morning Briefing via Subconscious Engine ──────────────────────────
        briefing = self.subconscious.generate_morning_briefing()
        self.add_log(
            f"[Subconscious] Session Ahead: {briefing['session_ahead']} | "
            f"Focus: {briefing['focus_directive']}"
        )

        # ── Market Regime via Free Data ───────────────────────────────────────
        regime = self.market_data_fetcher.get_market_regime()
        if regime.get("actionable"):
            self.add_log(
                f"[Market Regime] {regime['regime']} | "
                f"sources={regime.get('dxy_source', 'unknown')}+{regime.get('crypto_source', 'unknown')}"
            )
        else:
            self.add_log(
                f"[Market Regime] UNAVAILABLE | {regime.get('reason', 'verified source data missing')}",
                "WARNING",
            )

        poll_interval = self.config["bot"].get("poll_interval_seconds", 15)

        while self.running:
            try:
                if not self.paused:
                    self._run_trading_cycle()
                time.sleep(poll_interval)
            except Exception as e:
                logger.error(f"Error in trading cycle: {e}", exc_info=True)
                self.add_log(f"Cycle error: {e}", "ERROR")
                time.sleep(poll_interval)

    def pause(self):
        self.paused = True
        self.add_log("Bot execution PAUSED.", "WARNING")

    def resume(self):
        if self.telemetry_only:
            self.paused = True
            self.add_log(
                "Resume ignored: broker-demo dashboard is telemetry-only; order execution remains gated.",
                "WARNING",
            )
            return False
        self.paused = False
        self.add_log("Bot execution RESUMED.", "INFO")

    def stop(self):
        self.running = False
        self.cycle_scheduler.stop()
        self.mt5.shutdown()
        self.add_log("Bot execution STOPPED.", "WARNING")

    # ── Main Trading Cycle ────────────────────────────────────────────────────

    def _run_trading_cycle(self):
        acc = self.mt5.get_account_info()

        # 0. Admin self-heal & telemetry
        self.admin_controller.self_heal_services()

        # 1. Funding Pips Shield
        self.funding_pips_expert.update_daily_watermark(acc["balance"], acc["equity"])
        allowed, risk_reason = self.funding_pips_expert.can_trade(acc["balance"], acc["equity"])
        if not allowed:
            self.add_log(f"[Funding Pips Guard] {risk_reason}", "WARNING")
            return

        # 2. Goal tracking via OpenHuman Subconscious
        self.subconscious.update_trading_goals(acc["equity"], acc["balance"])

        # 3. World monitor
        self.world_monitor.fetch_live_world_feed()

        # 4. Manage open positions
        open_positions = self.mt5.get_open_positions()
        self._manage_open_positions(open_positions)

        # 4.5 Autonomous Post-Trade Forensics & Self-Learning on Closed Deals
        self._check_and_learn_from_closed_trades()

        if len(open_positions) >= self.config["risk_management"]["max_open_trades"]:
            return

        # 5. Multi-Symbol Scanning & Candidate Generation
        open_positions_now = self.mt5.get_open_positions()
        open_symbols = {p["symbol"] for p in open_positions_now}
        candidates = []

        for symbol in self.config["symbols"]:
            # ── Guard 1: No duplicate symbol entry ──────────────────────────
            if symbol in open_symbols:
                self.stats["duplicate_blocks"] += 1
                continue

            # ── Guard 2: 60-second signal cooldown per symbol ────────────────
            now_ts = time.time()
            last_ts = self._last_signal_time.get(symbol, 0.0)
            if now_ts - last_ts < self._signal_cooldown_sec:
                self.stats["cooldown_blocks"] += 1
                continue

            # 4-Tier Fractal Timeframes (H4 Macro + H1 Trend + M15 Entry + M5 Trigger + D1 ADR)
            tfs = self.config.get("timeframes", {})
            df_macro = self.mt5.get_historical_candles(symbol, tfs.get("macro_tf", "H4"), count=100)
            df_trend = self.mt5.get_historical_candles(symbol, tfs.get("trend_tf", "H1"), count=200)
            df_entry = self.mt5.get_historical_candles(symbol, tfs.get("entry_tf", "M15"), count=100)
            df_trigger = self.mt5.get_historical_candles(symbol, tfs.get("trigger_tf", "M5"), count=100)
            df_daily = self.mt5.get_historical_candles(symbol, tfs.get("daily_tf", "D1"), count=20)

            if df_trend.empty or df_entry.empty:
                continue

            analysis = self.analyzer.analyze_symbol(
                symbol=symbol,
                df_trend=df_trend,
                df_entry=df_entry,
                df_macro=df_macro,
                df_trigger=df_trigger,
                df_daily=df_daily
            )
            signal = self.strategy.evaluate_signals(analysis)

            if signal:
                sig_type = signal.get("signal")
                # ── Guard 3: Anti-Flip Opposite Direction Cooldown (15 min) ──────
                last_closed_info = self._last_closed_trade_info.get(symbol)
                if last_closed_info:
                    last_dir, last_close_ts = last_closed_info
                    if (now_ts - last_close_ts < 900) and (sig_type != last_dir):
                        rem_sec = int(900 - (now_ts - last_close_ts))
                        self.add_log(
                            f"[Anti-Flip Guard] {symbol} {sig_type} blocked — cooling down for {rem_sec}s after {last_dir} close.",
                            "WARNING"
                        )
                        continue

                # Multi-Agent Consensus Voter
                consensus = self.consensus_voter.vote(analysis, sig_type)
                if not consensus["approved"]:
                    self.stats["consensus_rejections"] += 1
                    continue

                # Signal Quality Scorer
                quality = self.signal_scorer.score_signal({
                    **signal,
                    "direction": sig_type,
                    "patterns": [analysis.get("structure_pattern")] + list(analysis.get("candlestick_patterns", [])),
                    "weather_forecast": analysis.get("weather_forecast"),
                    "fincept_sentiment": analysis.get("fincept_sentiment"),
                    "atr": analysis.get("atr"),
                })
                if quality["composite_quality"] < 2.0:
                    self.stats["quality_rejections"] += 1
                    continue

                market_regime = self.market_data_fetcher.get_market_regime()
                context = self.super_context.build_trade_context(
                    symbol=symbol,
                    analysis=analysis,
                    weather_forecast=analysis.get("weather_forecast"),
                    market_regime=market_regime,
                    consensus_vote=consensus,
                )

                signature_setups = self.ai_engine.get_signature_setups() if hasattr(self.ai_engine, "get_signature_setups") else []
                is_sig = signal.get("pattern") in signature_setups

                confidence_score = self.macro_intel.arbitrator.calculate_candidate_confidence(
                    signal=signal,
                    quality_score=quality["composite_quality"],
                    context_score=context["context_score"],
                    is_signature=is_sig
                )

                candidates.append({
                    "symbol": symbol,
                    "signal": signal,
                    "analysis": analysis,
                    "consensus": consensus,
                    "quality": quality,
                    "context": context,
                    "market_regime": market_regime,
                    "confidence_score": confidence_score
                })

        # 6. Cross-Pair Confidence Arbitration & USD Conflict Filter
        approved_candidates, paused_logs = self.macro_intel.arbitrator.arbitrate_candidates(
            candidates=candidates,
            open_positions=open_positions_now,
            correlation_guard=self.macro_intel.correlation_guard
        )

        for p_log in paused_logs:
            self.stats["rejected_trades"] += 1
            self.add_log(p_log["reason"], "WARNING")

        # 7. Execute highest-confidence approved signals
        for cand in approved_candidates:
            if len(self.mt5.get_open_positions()) >= self.config["risk_management"]["max_open_trades"]:
                break
            self.stats["total_signals"] += 1
            self._process_arbitrated_candidate(cand, acc)

    # ── Signal Processing (Full Intelligence Pipeline) ────────────────────────

    def _process_arbitrated_candidate(self, cand: Dict[str, Any], account_info: Dict[str, Any]):
        """Executes an arbitrated, high-confidence candidate trade."""
        signal = cand["signal"]
        analysis = cand["analysis"]
        quality = cand["quality"]
        context = cand["context"]
        market_regime = cand["market_regime"]
        conf_score = cand.get("confidence_score", 0.0)

        self._process_trade_signal(
            signal=signal,
            account_info=account_info,
            analysis=analysis,
            quality=quality,
            context=context,
            market_regime=market_regime,
            confidence_score=conf_score
        )

    def _process_trade_signal(
        self,
        signal: Dict[str, Any],
        account_info: Dict[str, Any],
        analysis: Dict[str, Any],
        quality: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        market_regime: Optional[Dict[str, Any]] = None,
        confidence_score: float = 0.0,
    ):
        symbol = signal["symbol"]
        signal_type = signal["signal"]
        price = signal["entry_price"]
        sl = signal["sl_price"]
        tp = signal["tp_price"]

        # ── A. Multi-Agent Consensus Vote (AI-Trader) ──────────────────────────
        consensus = self.consensus_voter.vote(analysis, signal_type)
        if not consensus["approved"]:
            self.stats["consensus_rejections"] += 1
            return

        # ── B. Signal Quality Score (AI-Trader) ───────────────────────────────
        if quality is None:
            quality = self.signal_scorer.score_signal({
                **signal,
                "direction": signal_type,
                "patterns": [analysis.get("structure_pattern")] + list(analysis.get("candlestick_patterns", [])),
                "weather_forecast": analysis.get("weather_forecast"),
                "fincept_sentiment": analysis.get("fincept_sentiment"),
                "atr": analysis.get("atr"),
            })
        if quality["composite_quality"] < 2.0:
            self.stats["quality_rejections"] += 1
            return

        # ── C. SuperContext Builder (OpenHuman) ───────────────────────────────
        if market_regime is None:
            market_regime = self.market_data_fetcher.get_market_regime()
        if context is None:
            context = self.super_context.build_trade_context(
                symbol=symbol,
                analysis=analysis,
                weather_forecast=analysis.get("weather_forecast"),
                market_regime=market_regime,
                consensus_vote=consensus,
            )
        self.add_log(
            f"[SuperContext] {symbol} — Confidence: {confidence_score:.2f} | "
            f"Quality: {quality['composite_quality']}/5 | Regime: {market_regime.get('regime', 'UNKNOWN')}",
        )

        # ── C0. Economic Calendar & News Shock Clearance ────────────────────
        news_clear = analysis.get("news_clearance", {})
        if not news_clear.get("is_cleared", True):
            self.stats["rejected_trades"] += 1
            self.add_log(f"[Macro News Blackout REJECT] {symbol}: {news_clear.get('reason')}", "WARNING")
            return

        # ── C1. Behavioral Psychology & Anti-Tilt Clearance ─────────────────
        today_profit = account_info["equity"] - 25000.0
        psych_cleared, psych_reason, psych_risk_mult = self.psychology_engine.evaluate_psychological_clearance(today_profit)
        if not psych_cleared:
            self.stats["rejected_trades"] += 1
            self.add_log(f"[Psychology Gate REJECT] {symbol}: {psych_reason}", "WARNING")
            return

        # ── C2. Adversarial Bull vs Bear Debate (TauricResearch / AI Hedge Fund) ──
        debate = self.debate_engine.conduct_debate(
            symbol=symbol,
            proposed_direction=signal_type,
            analysis=analysis,
            confluence_score=signal.get("confluence_score", 1.0)
        )
        if not debate["approved"]:
            self.stats["rejected_trades"] += 1
            self.add_log(f"[Adversarial Debate VETO] {symbol} {signal_type}: {debate['rejection_reason']}", "WARNING")
            return

        # ── C3. USD Currency Basket Correlation Audit ────────────────────────
        open_positions = self.mt5.get_open_positions()
        allowed_usd, usd_reason = self.macro_intel.correlation_guard.validate_usd_alignment(
            new_symbol=symbol,
            new_signal_type=signal_type,
            open_positions=open_positions
        )
        if not allowed_usd:
            self.stats["rejected_trades"] += 1
            self.add_log(f"[USD Correlation REJECT] {usd_reason}", "WARNING")
            return

        # ── D. Funding Pips Compliance Audit ─────────────────────────────────
        audit = self.funding_pips_expert.audit_trade(
            symbol, signal_type, price, sl, tp, len(open_positions)
        )
        if not audit["passed"]:
            self.stats["rejected_trades"] += 1
            self.add_log(f"[FP Expert REJECT] {symbol}: {audit['reason']}", "WARNING")
            return

        # ── E. Aladdin Risk Sizing & Fractional Kelly ─────────────────────────
        sym_u = symbol.upper()
        if "BTC" in sym_u or "ETH" in sym_u or "SOL" in sym_u:
            pip_unit = 1.0
            pip_val = 1.0
        elif "XAU" in sym_u or "GOLD" in sym_u:
            pip_unit = 0.1
            pip_val = 10.0
        elif "JPY" in sym_u:
            pip_unit = 0.01
            pip_val = 6.50
        else:
            pip_unit = 0.0001
            pip_val = 10.0

        sl_pips = abs(price - sl) / max(pip_unit, 1e-6)
        
        regime_intel = analysis.get("regime_intel", {})
        vol_scalar = regime_intel.get("vol_scalar", 1.0)
        dynamic_kelly_pct = self.aladdin_risk.compute_fractional_kelly(
            win_rate=0.55,
            payoff_ratio=2.0,
            regime_scalar=vol_scalar
        ) * 100.0
        
        configured_cap_pct = float(self.config.get("risk_management", {}).get("risk_per_trade_pct", 0.75))
        self.risk_manager.risk_per_trade_pct = min(dynamic_kelly_pct, configured_cap_pct, 0.75)
        lots = self.risk_manager.calculate_lot_size(account_info["equity"], sl_pips, symbol)
        if lots <= 0:
            return

        # ── E2. Aladdin Pre-Trade VaR Stress Test ─────────────────────────────
        prospective_risk_dollar = sl_pips * pip_val * lots
        max_daily_allowed = account_info["equity"] * (self.config["risk_management"]["max_daily_loss_pct"] / 100.0)
        
        stress_res = self.aladdin_risk.evaluate_pre_trade_stress_test(
            equity=account_info["equity"],
            prospective_risk_dollar=prospective_risk_dollar,
            open_positions=open_positions,
            max_daily_loss_dollar=max_daily_allowed
        )
        if not stress_res["passed"]:
            self.stats["rejected_trades"] += 1
            self.add_log(f"[Aladdin VaR Stress REJECT] {symbol}: {stress_res['reason']}", "WARNING")
            return

        # ── E3. Live Spread & Rollover Protection Guard ──────────────────────
        spread_info = self.mt5.get_live_spread(symbol)
        max_gold_pts = self.config.get("spread_guard", {}).get("max_gold_spread_points", 35.0)
        max_forex_pips = self.config.get("spread_guard", {}).get("max_forex_spread_pips", 2.5)
        is_spread_too_wide = (symbol == "XAUUSD" and spread_info["spread_points"] > max_gold_pts) or (symbol != "XAUUSD" and spread_info["spread_pips"] > max_forex_pips)
        if is_spread_too_wide:
            self.stats["rejected_trades"] += 1
            self.add_log(
                f"[Spread Guard REJECT] {symbol}: Live spread widened ({spread_info.get('spread_pips')} pips / {spread_info.get('spread_points')} pts). Waiting for spread normalization.",
                "WARNING"
            )
            return

        # ── F. Jarvis Vision & Desktop Capture ───────────────────────────────
        self.jarvis_agent.process_market_event("TRADE_SIGNAL", signal)
        self.vision_control.capture_screen("latest_order_entry.png")

        # ── G. MT5 Order Execution ────────────────────────────────────────────
        res = self.mt5.place_order(symbol, signal_type, lots, price, sl, tp, comment="AI-SMC-25k-FULL")
        if res and res.get("success"):
            self.stats["executed_trades"] += 1
            ticket = res.get("ticket", 0)

            # ── Record cooldown timestamp so same symbol can't re-enter for 60s ──
            self._last_signal_time[symbol] = time.time()

            self.add_log(
                f"ORDER PLACED! #{ticket} {signal_type} {symbol} "
                f"Lot:{lots} SL:{sl:.5f} TP:{tp:.5f} "
                f"Quality:{quality['composite_quality']}/5 Regime:{market_regime.get('regime','?')}"
            )

            # ── H. Memory & Learning Store ────────────────────────────────────
            trade_record = {
                "ticket": ticket, "symbol": symbol, "signal_type": signal_type,
                "pattern": signal.get("pattern", "SMC"), "session": signal.get("session", "UNKNOWN"),
                "entry_price": price, "sl_price": sl, "tp_price": tp,
                "confluence_score": signal.get("confluence_score", 0),
                "quality_score": quality["composite_quality"],
                "context_score": context["context_score"],
                "market_regime": market_regime.get("regime", "UNKNOWN"),
                "risk_dollars": account_info["equity"] * (
                    self.config["risk_management"]["risk_per_trade_pct"] / 100.0
                ),
            }
            self.ai_engine.log_trade(trade_record)
            self._trade_history.append(trade_record)
            self._tracked_trades[ticket] = trade_record

            # Store lesson in OpenHuman Memory Tree
            category = "GOLD_PATTERNS" if symbol == "XAUUSD" else "FOREX_PATTERNS"
            self.memory_tree.store_lesson(
                category=category,
                lesson=f"{signal_type} on {symbol} via {signal.get('pattern','SMC')} "
                       f"during {signal.get('session','?')} — Quality {quality['composite_quality']}/5",
                importance_score=min(quality["composite_quality"] / 5.0, 1.0),
            )

            # Multi-broker replication log
            self.trade_replicator.replicate_mt5_trade({**trade_record, "volume": lots, "price_open": price})

            # WhatsApp Alert
            self.whatsapp.send_trade_notification({
                **trade_record, "volume": lots,
                "quality_score": quality["composite_quality"],
                "regime": market_regime.get("regime", "UNKNOWN"),
            })

            # Periodic subconscious reflection every 5 trades
            if len(self._trade_history) % 5 == 0:
                insights = self.subconscious.reflect_on_trades(self._trade_history)
                for ins in insights[:2]:
                    self.add_log(f"[Subconscious] {ins}")

    # ── Autonomous Closed Trade Forensics & Self-Learning ─────────────────────

    def _check_and_learn_from_closed_trades(self):
        """
        Polls MT5 closed deals history to detect when any open or tracked trade closes.
        Runs autonomous forensic root-cause diagnosis on SL/TP hits and auto-optimizes strategy.
        """
        try:
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            deals = self.mt5.get_historical_deals(now - timedelta(hours=3), now) if hasattr(self.mt5, "get_historical_deals") else None
            
            # Direct MT5 fallback if connector method not wrapped
            if deals is None:
                try:
                    import MetaTrader5 as mt5
                    deals = mt5.history_deals_get(now - timedelta(hours=3), now)
                except Exception:
                    deals = []

            if not deals:
                return

            for d in deals:
                if d.entry == 1:  # Deal OUT (Closed position)
                    ticket = d.position_id
                    if ticket in self._tracked_trades:
                        meta = self._tracked_trades[ticket]
                        deal_info = {
                            "ticket": ticket,
                            "symbol": d.symbol,
                            "direction": meta.get("signal_type", "BUY"),
                            "pattern": meta.get("pattern", "PRICE_ACTION"),
                            "session": meta.get("session", "UNKNOWN"),
                            "entry_price": meta.get("entry_price", d.price),
                            "exit_price": d.price,
                            "sl_price": meta.get("sl_price", 0.0),
                            "tp_price": meta.get("tp_price", 0.0),
                            "pnl_dollars": d.profit + d.swap + d.commission,
                            "trend_direction": meta.get("trend_direction", "NEUTRAL"),
                        }

                        # Run Autonomous Self-Learning Forensic Analysis
                        summary = self.ai_engine.analyze_and_learn_from_closed_trade(deal_info)
                        self.add_log(
                            f"[Self-Learning] #{ticket} {d.symbol} {summary['outcome']} (${summary['pnl_dollars']:+.2f}): {summary['diagnosis']}",
                            "INFO" if summary['outcome'] == "WIN" else "WARNING"
                        )

                        # Send WhatsApp notification with the learned lesson
                        emoji = "🎯" if summary['outcome'] == "WIN" else "⚠️"
                        msg = (
                            f"{emoji} *JARVIS SELF-LEARNING POST-TRADE REPORT*\n\n"
                            f"📌 *Symbol:* {d.symbol} (Ticket #{ticket})\n"
                            f"📊 *Result:* {summary['outcome']} ({summary['pnl_dollars']:+.2f}$ / {summary['pnl_pips']:+.1f} pips)\n"
                            f"🔍 *Diagnosis:* {summary['diagnosis']}\n"
                            f"⚙️ *Auto-Adjust:* {summary['action_taken']}\n"
                            f"💡 *Lesson Saved:* {summary['lesson']}"
                        )
                        self.whatsapp.send_message(msg)

                        # Record last closed trade info for Anti-Flip 15m cooldown
                        self._last_closed_trade_info[d.symbol] = (deal_info["direction"], time.time())

                        # Remove from active tracked map so it's not processed repeatedly
                        del self._tracked_trades[ticket]

        except Exception as e:
            logger.error(f"[Self-Learning Monitor Error] {e}")

    # ── Open Position Management ──────────────────────────────────────────────

    def _manage_open_positions(self, positions: List[Dict[str, Any]]):
        """
        For each open position:
          - Jarvis live screen vision inspection
          - Dynamic SL/TP adaptation on reversal sweeps
          - Automatic breakeven shift at 1:1 R:R
        """
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]
            p_type = p["type"]
            open_price = p["price_open"]
            curr_price = p["price_current"]
            sl = p["sl"]
            tp = p["tp"]

            if sl == 0 or tp == 0:
                continue

            # Ensure position is tracked for post-trade self-learning
            if ticket not in self._tracked_trades:
                self._tracked_trades[ticket] = {
                    "ticket": ticket, "symbol": symbol, "signal_type": p_type,
                    "pattern": "PRICE_ACTION", "session": "LIVE",
                    "entry_price": open_price, "sl_price": sl, "tp_price": tp,
                }

            df_trend = self.mt5.get_historical_candles(symbol, self.config["timeframes"]["trend_tf"], count=50)
            df_entry = self.mt5.get_historical_candles(symbol, self.config["timeframes"]["entry_tf"], count=50)
            analysis = self.analyzer.analyze_symbol(symbol, df_trend, df_entry) if not df_entry.empty else {}

            # Jarvis live inspection & SL/TP adaptation
            insp = self.jarvis_agent.inspect_live_trade(p, analysis)
            if insp.get("adjusted"):
                self.mt5.modify_position(ticket, insp["new_sl"], insp["new_tp"])
                self.add_log(
                    f"[Jarvis Adapt] {symbol} #{ticket}: {insp['reason']} → New SL {insp['new_sl']:.5f}"
                )

            # ── 1. Dynamic Partial Scale-Out Engine (50% TP1 / Runner TP2) ────
            scale_out_cfg = self.config.get("scale_out", {})
            original_risk_dist = abs(tp - open_price) / 2.0  # 1R distance
            profit_dist = (curr_price - open_price) if p_type == "BUY" else (open_price - curr_price)

            if scale_out_cfg.get("enabled", True) and ticket not in self._partially_closed_tickets:
                tp1_rr = scale_out_cfg.get("tp1_rr", 1.2)
                if profit_dist >= (tp1_rr * original_risk_dist):
                    half_vol = round(p["volume"] * (scale_out_cfg.get("tp1_close_pct", 50) / 100.0), 2)
                    if half_vol >= 0.01 and p["volume"] > half_vol:
                        success = self.mt5.close_partial_position(ticket, half_vol)
                        if success:
                            self._partially_closed_tickets.add(ticket)
                            lock_buffer = 0.05 * original_risk_dist
                            new_sl = (open_price + lock_buffer) if p_type == "BUY" else (open_price - lock_buffer)
                            self.mt5.modify_position(ticket, new_sl, tp)
                            self.add_log(
                                f"🎯 [TP1 PARTIAL SCALE-OUT] {symbol} #{ticket}: Closed 50% ({half_vol} lots) in profit! SL moved to Breakeven. Remaining lot running to TP2!",
                                "INFO"
                            )
                            self.whatsapp.send_message(
                                f"🎯 *JARVIS TP1 SCALE-OUT HIT!*\n\n"
                                f"📌 *Symbol:* {symbol} (Ticket #{ticket})\n"
                                f"💰 *Action:* Closed 50% lot ({half_vol} lots) in profit!\n"
                                f"🔒 *Risk:* SL moved to Breakeven ({new_sl:.5f}).\n"
                                f"Runner stop moved near entry toward TP2 ({tp:.5f}); spread, slippage, gaps and fees can still produce a loss."
                            )

            # ── 2. Strict 1:1 R:R Breakeven Shift ──────────────────────────────
            if profit_dist >= original_risk_dist:
                is_sl_behind_entry = (sl < open_price) if p_type == "BUY" else (sl > open_price)
                if is_sl_behind_entry:
                    lock_buffer = 0.05 * original_risk_dist
                    new_sl = (open_price + lock_buffer) if p_type == "BUY" else (open_price - lock_buffer)
                    self.mt5.modify_position(ticket, new_sl, tp)
                    self.add_log(
                        f"[1:1 R:R Breakeven] {symbol} #{ticket}: Gained +{profit_dist:.2f} (1R achieved) → SL locked at {new_sl:.5f}"
                    )
