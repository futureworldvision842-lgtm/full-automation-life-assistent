"""
higgsfield_vision_engine.py — Higgsfield AI Multimodal Vision & Chart Intelligence Engine.
========================================================================================
Provides local, deterministic candlestick-geometry analysis and an optional Higgsfield
credential boundary.  This module does not claim a remote Higgsfield inference unless a
separate API client actually performs one.

Capabilities:
  1. Optional Higgsfield authentication header builder (credentials from environment only).
  2. Multi-Timeframe Candlestick Geometry & Visual Rejection Scoring (0-100%).
  3. Fair Value Gap (FVG) and Order Block (OB) Visual Confirmation Gate.
  4. Institutional Tearsheet & Visual Proof Markup Generator.
  5. Explicit local-analysis mode when no external vision service is configured.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import numpy as np

logger = logging.getLogger("HiggsfieldVisionEngine")


class HiggsfieldVisionEngine:
    """
    Higgsfield AI Multimodal Vision Engine for institutional trading chart analysis.
    """

    DEFAULT_KEY_ID = ""
    DEFAULT_KEY_SECRET = ""
    DEFAULT_BASE_URL = "https://api.higgsfield.ai/v1"

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.api_key_id = os.environ.get("HIGGSFIELD_API_KEY_ID", self.DEFAULT_KEY_ID)
        self.api_key_secret = os.environ.get("HIGGSFIELD_API_KEY_SECRET", self.DEFAULT_KEY_SECRET)
        self.base_url = self.DEFAULT_BASE_URL
        self.model = "local-candle-geometry"
        self.enabled = False

        self._load_config()
        self.output_dir = "data/visual_reports"
        os.makedirs(self.output_dir, exist_ok=True)

        self.api_authenticated = bool(self.enabled and self.api_key_id and self.api_key_secret)
        logger.info(
            "Vision engine initialized (remote_enabled=%s, authenticated=%s, model=%s)",
            self.enabled,
            self.api_authenticated,
            self.model,
        )

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    h_cfg = cfg.get("higgsfield", {})
                    self.enabled = bool(h_cfg.get("enabled", False))
                    self.api_key_id = os.environ.get("HIGGSFIELD_API_KEY_ID", h_cfg.get("api_key_id", self.api_key_id))
                    self.api_key_secret = os.environ.get("HIGGSFIELD_API_KEY_SECRET", h_cfg.get("api_key_secret", self.api_key_secret))
                    self.base_url = h_cfg.get("base_url", self.base_url)
                    self.model = h_cfg.get("model", self.model)
            except Exception as e:
                logger.warning(f"Error loading Higgsfield config: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Return headers without leaking empty or unconfigured credentials."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Higgsfield-TradingBot-VisionClient/2.0"
        }
        if self.api_authenticated:
            headers["X-API-Key-ID"] = self.api_key_id
            headers["X-API-Key-Secret"] = self.api_key_secret
        return headers

    def audit_candlestick_rejection_visually(
        self,
        df_m15: pd.DataFrame,
        direction: str,
        symbol: str = "XAUUSD"
    ) -> Dict[str, Any]:
        """
        Visual Candlestick Rejection Audit Skill:
        Calculates exact wick-to-body ratios, candle absorption geometry, and returns
        a visual conviction score [0.0 - 100.0]% for trade gating.
        """
        if df_m15 is None or len(df_m15) < 3:
            return {
                "symbol": symbol,
                "direction": direction,
                "visual_conviction": 0.0,
                "is_clean_rejection": False,
                "reason": "Insufficient candles; confirmation unavailable",
                "body_ratio_pct": 0.0,
                "upper_wick_pct": 0.0,
                "lower_wick_pct": 0.0,
                "engine": "LOCAL_CANDLE_GEOMETRY",
                "data_mode": "INSUFFICIENT_DATA",
            }

        latest = df_m15.iloc[-1]
        prev = df_m15.iloc[-2]

        open_p = float(latest.get('open', 0.0))
        close_p = float(latest.get('close', 0.0))
        high_p = float(latest.get('high', 0.0))
        low_p = float(latest.get('low', 0.0))

        total_range = max(high_p - low_p, 1e-6)
        body_size = abs(close_p - open_p)
        upper_wick = high_p - max(open_p, close_p)
        lower_wick = min(open_p, close_p) - low_p

        body_ratio = body_size / total_range
        lower_wick_ratio = lower_wick / total_range
        upper_wick_ratio = upper_wick / total_range

        if direction.upper() == "BUY":
            # Bullish rejection: lower wick absorbs sell orders (Turtle soup / liquidity sweep)
            is_rejection = lower_wick_ratio >= 0.35 or (close_p > open_p and close_p >= prev.get('high', close_p))
            conviction = min(100.0, (lower_wick_ratio * 100.0) + (40.0 if close_p > open_p else 15.0))
            reason = f"Bullish lower wick absorption: {lower_wick_ratio*100:.1f}% of range | Body: {body_ratio*100:.1f}%"
        else:  # SELL
            # Bearish rejection: upper wick absorbs buy orders
            is_rejection = upper_wick_ratio >= 0.35 or (close_p < open_p and close_p <= prev.get('low', close_p))
            conviction = min(100.0, (upper_wick_ratio * 100.0) + (40.0 if close_p < open_p else 15.0))
            reason = f"Bearish upper wick absorption: {upper_wick_ratio*100:.1f}% of range | Body: {body_ratio*100:.1f}%"

        return {
            "symbol": symbol,
            "direction": direction.upper(),
            "visual_conviction": round(conviction, 1),
            "is_clean_rejection": bool(is_rejection),
            "reason": reason,
            "body_ratio_pct": round(body_ratio * 100.0, 1),
            "lower_wick_pct": round(lower_wick_ratio * 100.0, 1),
            "upper_wick_pct": round(upper_wick_ratio * 100.0, 1),
            "engine": "LOCAL_CANDLE_GEOMETRY",
            "data_mode": "OBSERVED_CANDLES",
        }

    def evaluate_smc_visual_confirmation(
        self,
        symbol: str,
        direction: str,
        df_candles: pd.DataFrame,
        smc_intel: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Multimodal visual confirmation uniting candle geometry and SMC dealing range.
        Returns visual confirmation verdict, confidence score, and visual markup metadata.
        """
        audit = self.audit_candlestick_rejection_visually(df_candles, direction, symbol=symbol)
        
        ote = smc_intel.get("ote", {})
        fvgs = smc_intel.get("fvgs", [])
        order_blocks = smc_intel.get("order_blocks", [])

        in_discount = ote.get("in_ote_discount", True) if direction == "BUY" else ote.get("in_ote_premium", True)
        has_active_fvg = len(fvgs) > 0
        has_active_ob = len(order_blocks) > 0

        # Composite score
        base_conviction = audit["visual_conviction"]
        smc_bonus = (15.0 if in_discount else 0.0) + (10.0 if has_active_fvg else 0.0) + (10.0 if has_active_ob else 0.0)
        final_confidence = min(100.0, base_conviction + smc_bonus)
        verdict = "APPROVED" if final_confidence >= 70.0 and audit["is_clean_rejection"] else "CAUTION_FLAGGED"

        return {
            "symbol": symbol,
            "direction": direction,
            "verdict": verdict,
            "confidence_pct": round(final_confidence, 1),
            "visual_rejection": audit,
            "smc_alignment": {
                "in_discount_or_premium": in_discount,
                "active_fvgs_count": len(fvgs),
                "active_obs_count": len(order_blocks)
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": self.model,
            "remote_inference_used": False,
        }

    def generate_visual_tearsheet(
        self,
        account_info: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        macro_sentiment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generates structured visual tear-sheet report."""
        balance = float(account_info.get("balance", 0.0))
        equity = float(account_info.get("equity", balance))
        starting_balance = float(account_info.get("starting_balance", balance))
        net_profit = equity - starting_balance
        pnl_pct = (net_profit / starting_balance) * 100.0 if starting_balance > 0 else 0.0
        available = bool(account_info.get("available", True)) and starting_balance > 0
        health = "DATA AVAILABLE" if available else "DATA UNAVAILABLE"

        tearsheet_text = (
            f"🖼️ *HIGGSFIELD AI VISUAL TEAR-SHEET*\n"
            f"═════════════════════════════\n"
            f"💰 *Balance:* ${balance:,.2f} | *Equity:* ${equity:,.2f}\n"
            f"📈 *Net Return:* ${net_profit:+,.2f} ({pnl_pct:+.2f}%)\n"
            f"📊 *Open Positions:* {len(open_positions)}\n"
            f"🌐 *Macro Regime:* {macro_sentiment.get('macro_bias', 'NEUTRAL')}\n"
            f"🛡️ *Account Telemetry:* {health}\n"
            f"═════════════════════════════"
        )

        return {
            "tearsheet_text": tearsheet_text,
            "net_profit": round(net_profit, 2),
            "pnl_pct": round(pnl_pct, 2),
            "status": "AVAILABLE" if available else "UNAVAILABLE",
            "api_authenticated": self.api_authenticated,
            "remote_inference_used": False,
            "engine": "LOCAL_CANDLE_GEOMETRY",
        }
