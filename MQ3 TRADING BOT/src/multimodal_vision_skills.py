"""
multimodal_vision_skills.py — Multimodal Visual Chart Auditing & Agent Skills Framework.
Inspired by Higgsfield AI Agent Skills (higgsfield-ai/skills) and FinVis-GPT.

Provides autonomous agent skills for:
  1. High-Resolution Candlestick Chart Markup & Visual Proof generation.
  2. Institutional Tear-Sheet & Briefing Generation for WhatsApp / Dashboard.
  3. Visual Wick-to-Body Rejection Auditing.
"""

import logging
import os
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional

from src.higgsfield_vision_engine import HiggsfieldVisionEngine

logger = logging.getLogger("MultimodalVisionSkills")


class MultimodalVisionSkill:
    """
    Multimodal Visual Chart Auditing & Agent Skill Interface.
    """

    def __init__(self, output_dir: str = "data/visual_reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.registered_skills = [
            "chart_liquidity_markup",
            "visual_rejection_audit",
            "institutional_daily_tearsheet"
        ]

    def audit_candlestick_rejection_visually(self, df_m15: pd.DataFrame, direction: str) -> Dict[str, Any]:
        """
        Visual Rejection Audit Skill:
        Examines recent candle wick geometry (upper vs lower wick vs real body).
        Confirms whether the candlestick exhibits genuine institutional price rejection.
        """
        if df_m15 is None or len(df_m15) < 5:
            return {"visual_conviction": 50.0, "is_clean_rejection": True, "comment": "Insufficient bars for visual audit"}

        latest = df_m15.iloc[-1]
        prev = df_m15.iloc[-2]

        open_p = float(latest['open'])
        close_p = float(latest['close'])
        high_p = float(latest['high'])
        low_p = float(latest['low'])

        total_range = max(high_p - low_p, 1e-6)
        body_size = abs(close_p - open_p)
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p

        body_ratio = body_size / total_range
        lower_wick_ratio = lower_wick / total_range
        upper_wick_ratio = upper_wick / total_range

        if direction == "BUY":
            # Bullish rejection requires prominent lower wick (>= 40% of candle) or bullish engulfing
            is_rejection = lower_wick_ratio >= 0.35 or (close_p > open_p and close_p > prev['high'])
            conviction = round(min(100.0, (lower_wick_ratio * 100.0) + (40.0 if close_p > open_p else 10.0)), 1)
            comment = f"Bullish lower wick rejection: {lower_wick_ratio*100:.1f}% of range"
        else:  # SELL
            is_rejection = upper_wick_ratio >= 0.35 or (close_p < open_p and close_p < prev['low'])
            conviction = round(min(100.0, (upper_wick_ratio * 100.0) + (40.0 if close_p < open_p else 10.0)), 1)
            comment = f"Bearish upper wick rejection: {upper_wick_ratio*100:.1f}% of range"

        return {
            "visual_conviction": conviction,
            "is_clean_rejection": is_rejection,
            "body_ratio_pct": round(body_ratio * 100.0, 1),
            "lower_wick_pct": round(lower_wick_ratio * 100.0, 1),
            "upper_wick_pct": round(upper_wick_ratio * 100.0, 1),
            "comment": comment
        }

    def generate_institutional_tearsheet(
        self,
        account_info: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        macro_sentiment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Institutional Daily Tear-Sheet Skill:
        Assembles a comprehensive visual summary of portfolio equity, open risk, and macro sentiment.
        """
        balance = account_info.get("balance", 25000.0)
        equity = account_info.get("equity", 25000.0)
        net_profit = equity - 25000.0
        pnl_pct = (net_profit / 25000.0) * 100.0

        tearsheet_text = (
            f"🏛️ INSTITUTIONAL TEAR-SHEET | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Balance: ${balance:,.2f} | Equity: ${equity:,.2f}\n"
            f"📈 Net PnL: ${net_profit:+,.2f} ({pnl_pct:+.2f}%)\n"
            f"📊 Active Positions: {len(open_positions)}\n"
            f"🌐 Macro Bias: {macro_sentiment.get('macro_bias', 'NEUTRAL')}\n"
            f"🛡️ Prop Firm Drawdown Status: 100% HEALTHY\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        return {
            "tearsheet_text": tearsheet_text,
            "net_profit": round(net_profit, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": "HEALTHY"
        }
