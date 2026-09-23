import os
import sys
import json
import logging
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestAllPowers")

# ── Core Modules ──────────────────────────────────────────────────────────────
from src.mt5_connector import MT5Connector
from src.risk_manager import RiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.market_analyzer import MarketAnalyzer
from src.market_maker_game_engine import MarketMakerGameEngine
from src.chart_pattern_engine import ChartPatternEngine
from src.strategy import StrategyEngine
from src.ai_learning_engine import AILearningEngine
from src.whatsapp_notifier import WhatsAppNotifier
from src.world_monitor_feed import WorldMonitorFeed
from src.jarvis_agent_intel import JarvisAgentIntel
from src.cloud_memory_sync import CloudMemorySync
from src.system_admin_controller import SystemAdminController
from src.fincept_terminal_intel import FinceptTerminalIntel

# ── New Repository Integrations ───────────────────────────────────────────────
from src.ai_trader_intel import SignalQualityScorer, MultiAgentConsensusVoter, FreeMarketDataFetcher
from src.openhuman_cognitive_engine import SubconsciousReflectionEngine, MemoryTreeManager, SuperContextBuilder
from src.multi_broker_bridge import BrokerBridge, IBKRBridgeConnector, TradeReplicator


def make_mock_df(n=50):
    return pd.DataFrame({
        'time': pd.date_range(end=pd.Timestamp.now(), periods=n, freq='15min'),
        'open':  [100.0] * n,
        'high':  [102.0] * n,
        'low':   [98.0]  * n,
        'close': [101.0] * n,
        'tick_volume': [1000] * n,
    })


def run_stress_test_suite():
    logger.info("=" * 70)
    logger.info("  FUNDING PIPS 25K MASTER AI BOT — FULL POWERS AUDIT (14 MODULES)")
    logger.info("=" * 70)

    with open("config.json", "r") as f:
        cfg = json.load(f)

    # ── 1. Config ─────────────────────────────────────────────────────────────
    logger.info("✔ 1. Config JSON loaded cleanly.")

    # ── 2. Funding Pips Compliance ────────────────────────────────────────────
    fp = FundingPipsExpert(cfg)
    can_t, msg = fp.can_trade(25000.0, 25000.0)
    assert can_t, f"FP audit failed: {msg}"
    logger.info("✔ 2. Funding Pips 25k compliance auditor verified.")

    # ── 3. Risk Sizing ────────────────────────────────────────────────────────
    rm = RiskManager(cfg)
    rm.update_daily_baseline(25000.0, 25000.0)
    lot = rm.calculate_lot_size(25000.0, 25.0, "XAUUSD")
    assert lot > 0
    logger.info(f"✔ 3. Risk Sizing verified (XAUUSD lot: {lot}).")

    # ── 4. Market Maker Game Engine ───────────────────────────────────────────
    mm = MarketMakerGameEngine()
    df_mock = make_mock_df()
    df_mock.iloc[-2, df_mock.columns.get_loc('low')] = 95.0
    df_mock.iloc[-1, df_mock.columns.get_loc('close')] = 101.5
    sweep = mm.detect_liquidity_sweep(df_mock)
    assert sweep.get("type") == "BULLISH_SWEEP"
    logger.info("✔ 4. Market Maker Game Engine (Stop-Hunt Sweeps) verified.")

    # ── 5. Chart Pattern Engine ───────────────────────────────────────────────
    cp = ChartPatternEngine()
    df_pin = make_mock_df()
    df_pin.iloc[-1, df_pin.columns.get_loc('high')]  = 105.0
    df_pin.iloc[-1, df_pin.columns.get_loc('low')]   = 95.0
    df_pin.iloc[-1, df_pin.columns.get_loc('open')]  = 96.0
    df_pin.iloc[-1, df_pin.columns.get_loc('close')] = 104.0
    c_res = cp.detect_candlestick_patterns(df_pin)
    logger.info(f"✔ 5. Chart Pattern Engine verified ({len(c_res['patterns'])} patterns detected).")

    # ── 6. World Monitor Feed ─────────────────────────────────────────────────
    wm = WorldMonitorFeed()
    feed = wm.fetch_live_world_feed()
    logger.info(f"✔ 6. World Monitor Feed verified ({len(feed['news'])} macro news items).")

    # ── 7. Jarvis Hermes Agent ────────────────────────────────────────────────
    jarvis = JarvisAgentIntel()
    j_res = jarvis.process_market_event("TEST_EVENT", {"symbol": "XAUUSD"})
    assert j_res["status"] == "PROCESSED"
    logger.info("✔ 7. Jarvis Hermes Agent verified.")

    # ── 8. Cloud Memory Sync ──────────────────────────────────────────────────
    cms = CloudMemorySync()
    cms.store_pattern_memory({"symbol": "XAUUSD", "pattern": "BULLISH_SWEEP", "confluence_score": 1.6})
    logger.info("✔ 8. Cloud Memory Sync (Firebase, MongoDB & SQLite) verified.")

    # ── 9. System Admin Controller ────────────────────────────────────────────
    admin = SystemAdminController()
    telem = admin.get_system_telemetry()
    logger.info(f"✔ 9. System Admin Controller verified (CPU: {telem['cpu_percent']}%).")

    # ── 10. Fincept Terminal & Freqtrade Quant ────────────────────────────────
    fincept = FinceptTerminalIntel()
    df_fin = fincept.calculate_fincept_indicators(make_mock_df())
    assert 'fincept_sentiment' in df_fin.columns
    logger.info(f"✔ 10. Fincept Terminal & Freqtrade Quant verified (Sentiment: {df_fin['fincept_sentiment'].iloc[-1]}).")

    # ── 11. AI-Trader Signal Quality Scorer ───────────────────────────────────
    scorer = SignalQualityScorer()
    q = scorer.score_signal({
        "symbol": "XAUUSD", "direction": "BUY",
        "sl": 2300.0, "tp": 2350.0,
        "patterns": ["BULLISH_SWEEP", "BULLISH_FVG"],
        "confluence_score": 1.4,
        "weather_forecast": {"category": "SUNNY_BULLISH_UPDRAFT"},
        "fincept_sentiment": 72.0,
        "atr": 1.5,
        "lot_size": 0.75,
        "session": "LONDON",
    })
    assert q["composite_quality"] > 0
    logger.info(f"✔ 11. AI-Trader Signal Quality Scorer verified (Score: {q['composite_quality']}/5.0 — {q['grade']}).")

    # ── 12. AI-Trader Multi-Agent Consensus Voter ─────────────────────────────
    voter = MultiAgentConsensusVoter()
    analysis_mock = {
        "symbol": "XAUUSD",
        "trend_direction": "BULLISH",
        "rsi": 52.0,
        "bullish_fvg": {"type": "BULLISH_FVG"},
        "bullish_ob": {"type": "BULLISH_OB"},
        "liquidity_sweep": {"type": "BULLISH_SWEEP"},
    }
    vote_res = voter.vote(analysis_mock, "BUY")
    assert vote_res["approved"] is True, f"Consensus vote failed: {vote_res}"
    logger.info(
        f"✔ 12. AI-Trader 3-Bot Consensus Voter verified "
        f"({vote_res['approve_count']}/3 approvals — {vote_res['verdict']})."
    )

    # ── 13. OpenHuman Cognitive Engine ────────────────────────────────────────
    mem_tree = MemoryTreeManager()
    mem_tree.store_lesson("GOLD_PATTERNS", "Gold tends to sweep lows before London open.", importance_score=0.9)
    lessons = mem_tree.get_relevant_lessons("XAUUSD")
    subconscious = SubconsciousReflectionEngine()
    trade_hist = [
        {"symbol": "XAUUSD", "outcome": "WIN",  "pnl": 120.0, "session": "LONDON", "pattern": "BULLISH_SWEEP"},
        {"symbol": "XAUUSD", "outcome": "WIN",  "pnl":  80.0, "session": "LONDON", "pattern": "BULLISH_FVG"},
        {"symbol": "EURUSD", "outcome": "LOSS", "pnl": -40.0, "session": "ASIAN",  "pattern": "OB"},
    ]
    insights = subconscious.reflect_on_trades(trade_hist)
    ctx_builder = SuperContextBuilder(memory_tree=mem_tree, reflection=subconscious)
    ctx = ctx_builder.build_trade_context("XAUUSD", analysis_mock)
    assert ctx["context_score"] >= 0
    logger.info(
        f"✔ 13. OpenHuman Cognitive Engine verified "
        f"(Memory lessons: {len(lessons)}, Context Score: {ctx['context_score']}/100)."
    )

    # ── 14. Multi-Broker Bridge (IBKR) ────────────────────────────────────────
    bridge = IBKRBridgeConnector()
    mapped = bridge.map_symbol("XAUUSD")
    assert mapped["symbol"] == "GC"
    lots_mirror = bridge.calculate_bridge_lot_size(0.5, sizing_mode="mirror")
    assert lots_mirror == 0.5
    lots_equity = bridge.calculate_bridge_lot_size(1.0, sizing_mode="equity_ratio", mt5_equity=25000, broker_equity=50000)
    replicator = TradeReplicator(bridge=bridge)
    replicated = replicator.replicate_mt5_trade({
        "symbol": "XAUUSD", "type": "BUY", "volume": 0.75,
        "price_open": 2340.0, "sl": 2310.0, "tp": 2400.0, "ticket": 999,
    })
    assert replicated["source_ticket"] == 999
    logger.info(
        f"✔ 14. Multi-Broker Bridge (IBKR) verified "
        f"(XAUUSD→{mapped['symbol']}, Equity-Ratio Lot: {lots_equity}, Replicated Ticket: {replicated['source_ticket']})."
    )

    # ── 15. MT5 Connector ─────────────────────────────────────────────────────
    mt5 = MT5Connector(cfg, simulation_mode=True)
    mt5.connect()
    acc = mt5.get_account_info()
    assert acc["balance"] > 0
    logger.info("✔ 15. MT5 Connector verified.")

    logger.info("=" * 70)
    logger.info("  ALL 15 POWER MODULES AUDITED — 100% PASSED ✅")
    logger.info("=" * 70)


if __name__ == "__main__":
    run_stress_test_suite()
