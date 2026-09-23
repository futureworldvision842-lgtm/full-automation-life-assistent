import json
import logging
import datetime

from src.mt5_connector import MT5Connector
from src.risk_manager import RiskManager
from src.funding_pips_expert import FundingPipsExpert
from src.macro_intelligence import GlobalMacroGeopoliticalIntelligence
from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.backtester import Backtester
from src.institutional_knowledge import InstitutionalKnowledge
from src.ai_learning_engine import AILearningEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestSystem")

def test_full_bot_pipeline():
    logger.info("--- 1. Testing Config Load ---")
    with open("config.json", "r") as f:
        config = json.load(f)
    assert config["account_info"]["target_account_size"] == 25000.0
    logger.info("Config OK.")

    logger.info("--- 2. Testing Funding Pips Expert Compliance Rules ---")
    fp_expert = FundingPipsExpert("25k")
    passed, msg = fp_expert.audit_trade_compliance("EURUSD", 1.0850, 1.0830, 25000.0, 25000.0, 0)
    assert passed is True
    logger.info(f"Funding Pips Audit: {msg}")

    logger.info("--- 3. Testing Global Macro & Geopolitical Intelligence ---")
    macro = GlobalMacroGeopoliticalIntelligence()
    locked, macro_msg = macro.is_symbol_news_locked("EURUSD")
    logger.info(f"Macro Intel Scan: {macro_msg}")

    logger.info("--- 4. Testing AI Self-Learning Engine ---")
    ai_engine = AILearningEngine(db_path="data/test_memory.db")
    summary = ai_engine.get_ai_learning_summary()
    assert "total_trades_logged" in summary
    logger.info(f"AI Memory Summary: {summary}")

    logger.info("--- 5. Testing MT5 Connector (Simulation Mode) ---")
    mt5 = MT5Connector(simulation_mode=True)
    assert mt5.initialize() is True
    acc = mt5.get_account_info()
    assert acc["balance"] == 25000.0
    df_h1 = mt5.get_rates("EURUSD", "H1", num_candles=100)
    df_m15 = mt5.get_rates("EURUSD", "M15", num_candles=100)
    logger.info("MT5 Connector OK.")

    logger.info("--- 6. Testing Strategy & AI Pattern Weighting ---")
    analyzer = MarketAnalyzer(config)
    analysis = analyzer.analyze_symbol("EURUSD", df_h1, df_m15)
    strat = StrategyEngine(config, ai_engine=ai_engine)
    signal = strat.evaluate_signals(analysis)
    logger.info(f"AI Signal result: {signal if signal else 'HOLD / No Signal'}")

    logger.info("=========================================================")
    logger.info(" ALL FUNDING PIPS EXPERT & MACRO AI TESTS PASSED CLEANLY!")
    logger.info("=========================================================")

if __name__ == "__main__":
    test_full_bot_pipeline()
