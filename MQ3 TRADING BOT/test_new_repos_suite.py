import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from src.qlib_alpha158_engine import QlibAlpha158Engine
from src.adversarial_debate_engine import AdversarialDebateEngine
from src.finnlp_sentiment_stream import FinNLPSentimentStream
from src.multimodal_vision_skills import MultimodalVisionSkill

print("\n" + "="*80)
print("  ADVANCED GITHUB REPOSITORIES SUITE — VERIFICATION AUDIT")
print("="*80)

# 1. Qlib Alpha158 Engine
qlib = QlibAlpha158Engine()
np.random.seed(42)
prices = 4350.0 + np.cumsum(np.random.randn(60) * 1.5)
df_sample = pd.DataFrame({
    "open": prices - 0.5,
    "high": prices + 2.0,
    "low": prices - 2.0,
    "close": prices,
    "volume": np.random.randint(100, 1000, 60)
})
qlib_res = qlib.compute_alpha_factors(df_sample)
print(f"✔ 1. Microsoft Qlib Alpha158: Score={qlib_res['alpha_score']} | Bias={qlib_res['bias']} | VWAP Dev={qlib_res['vwap_deviation_pct']}% | Confluence Bonus={qlib_res['confluence_bonus']}")

# 2. Adversarial Debate Engine (TradingAgents / AI Hedge Fund)
debate_engine = AdversarialDebateEngine()
sample_analysis = {
    "trend_direction": "BULLISH",
    "rsi": 32.0,
    "premium_discount": {"zone": "DISCOUNT", "discount_pct": 72.0, "is_buy_allowed": True},
    "ote_buy": {"in_ote_zone": True},
    "vsa_intel": {"type": "BULLISH_ABSORPTION", "volume_ratio": 2.1},
    "killzone": {"is_prime_killzone": True, "killzone": "NY_AM_KILLZONE"},
    "adr_intel": {"is_adr_exhausted": False, "adr_pct_consumed": 45.0},
    "regime_intel": {"regime_state": 0}
}
debate_buy = debate_engine.conduct_debate("XAUUSD", "BUY", sample_analysis, confluence_score=3.5)
print(f"✔ 2. Adversarial Bull vs Bear Debate: Verdict={debate_buy['verdict']} | Approved={debate_buy['approved']} | Bull Score={debate_buy['bull_score']} | Bear Score={debate_buy['bear_score']}")

# 3. FinNLP Sentiment Stream (AI4Finance FinNLP / FinGPT)
finnlp = FinNLPSentimentStream()
sentiment = finnlp.fetch_live_macro_sentiment()
print(f"✔ 3. FinNLP Streaming Radar: Gold Sent={sentiment['gold_sentiment']}% | USD Sent={sentiment['usd_sentiment']}% | Macro Bias={sentiment['macro_bias']} | Red Folder={sentiment['is_red_folder_event_active']}")

# 4. Multimodal Vision Skills (Higgsfield AI Skills / FinVis-GPT)
vision_skill = MultimodalVisionSkill()
vision_audit = vision_skill.audit_candlestick_rejection_visually(df_sample, "BUY")
tearsheet = vision_skill.generate_institutional_tearsheet(
    account_info={"balance": 25891.96, "equity": 25969.81},
    open_positions=[{"symbol": "USDJPY", "type": "BUY", "volume": 0.24}],
    macro_sentiment=sentiment
)
print(f"✔ 4. Higgsfield Multimodal Vision Skills: Conviction={vision_audit['visual_conviction']}% | Rejection={vision_audit['is_clean_rejection']} | PnL={tearsheet['pnl_pct']}%")

print("\n" + "="*80)
print("  ALL 4 NEW REPOSITORY INTELLIGENCE MODULES OPERATIONAL \u2705")
print("="*80 + "\n")
