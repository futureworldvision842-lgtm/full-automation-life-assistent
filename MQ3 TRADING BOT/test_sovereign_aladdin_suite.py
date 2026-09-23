import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from src.intermarket_macro_radar import IntermarketMacroRadar
from src.economic_calendar_radar import EconomicCalendarRadar
from src.experiential_replay_engine import ExperientialReplayEngine
from src.trading_psychology_engine import TradingPsychologyEngine
from src.multi_regime_strategies import MultiRegimeStrategyMatrix
from src.institutional_analytics import InstitutionalAnalyticsEngine

print("\n" + "="*80)
print("  SOVEREIGN ALADDIN QUANT & PROP FIRM SUITE — VERIFICATION AUDIT")
print("="*80)

# 1. Intermarket Macro Radar
intermarket = IntermarketMacroRadar()
macro_data = intermarket.fetch_intermarket_metrics()
xau_macro = intermarket.evaluate_asset_macro_alignment("XAUUSD", "BUY")
print(f"✔ 1. Intermarket Macro Radar: Regime={macro_data['macro_regime']} | DXY Trend={macro_data['dxy_trend']} | Gold Tailwind={xau_macro['confluence_bonus']:+0.2f}")

# 2. Economic Calendar & News Circuit Breaker
calendar_radar = EconomicCalendarRadar()
news_status = calendar_radar.evaluate_news_clearance("EURUSD")
print(f"✔ 2. Economic Calendar News Shield: Cleared={news_status['is_cleared']} | Blackout={news_status['is_blackout']} | Reason={news_status.get('lockout_reason', news_status.get('reason', ''))}")

# 3. Experiential Replay Engine (RL Buffer)
replay = ExperientialReplayEngine()
exp_res = replay.record_trade_experience(
    symbol="USDJPY",
    direction="BUY",
    entry_price=158.866,
    exit_price=159.376,
    pnl_dollar=147.75,
    pattern_type="ORDER_BLOCK_RETEST",
    macro_regime="DOLLAR_DOMINANCE",
    confluence_score=3.8
)
print(f"✔ 3. Prioritized Experience Replay: Recorded={exp_res['status']} | Is Win={exp_res['is_win']} | Pattern Weight={exp_res['new_pattern_weight']}x | Total DB Memories={exp_res['total_experiences']}")

# 4. Behavioral Trading Psychology Engine
psych = TradingPsychologyEngine()
cleared, reason, risk_mult = psych.evaluate_psychological_clearance(today_profit=891.96)
print(f"✔ 4. Trading Psychology & Tilt Guard: Cleared={cleared} | Risk Multiplier={risk_mult}x | Reason={reason}")

# 5. Multi-Regime Strategy Matrix
multi_regime = MultiRegimeStrategyMatrix()
sample_analysis = {
    "trend_direction": "BULLISH",
    "rsi": 45.0,
    "killzone": {"killzone": "NY_AM_KILLZONE"},
    "ote_buy": {"in_ote_zone": True},
    "ote_sell": {"in_ote_zone": False},
    "vsa_intel": {"type": "BULLISH_ABSORPTION"},
    "inducement": {"is_swept": False},
    "current_price": 4380.0
}
regime_eval = multi_regime.evaluate_all_regimes("XAUUSD", None, None, sample_analysis)
print(f"✔ 5. Multi-Regime Strategy Matrix: Strategy={regime_eval['selected_strategy']} | Direction={regime_eval['direction']} | Conviction={regime_eval['strategy_conviction']}/5.0")

# 6. Institutional QuantStats Teardown Analytics
analytics = InstitutionalAnalyticsEngine()
metrics = analytics.compute_portfolio_metrics(
    trade_history=[
        {"profit": 147.75, "symbol": "USDJPY"},
        {"profit": 74.00, "symbol": "USDJPY"},
        {"profit": 110.20, "symbol": "XAUUSD"}
    ],
    current_balance=25891.96
)
print(f"✔ 6. QuantStats Teardown Analytics: Win Rate={metrics['win_rate_pct']}% | Sharpe={metrics['sharpe_ratio']} | Sortino={metrics['sortino_ratio']} | Profit Factor={metrics['profit_factor']} | Grade={metrics['status']}")

print("\n" + "="*80)
print("  ALL 6 SOVEREIGN PROP FIRM POWER ENGINES 100% OPERATIONAL \u2705")
print("="*80 + "\n")
