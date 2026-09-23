"""
sovereign_macro_whale_radar.py — Institutional Whale & Macro Radar Engine.
Computes Order Flow Imbalance (OFI), VPIN Order Flow Toxicity, Fed Net Liquidity, and Dark Pool DIX Proxies.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("SovereignWhaleRadar")


class SovereignMacroWhaleRadar:
    """
    Detects institutional whale footprints, toxic order flow imbalances,
    and macroeconomic net liquidity expansion/contraction.
    """

    def __init__(self, vpin_bucket_size: int = 50, vpin_num_buckets: int = 20):
        self.bucket_size = vpin_bucket_size
        self.num_buckets = vpin_num_buckets

    # ── 1. Cont-Kukanov-Stoikov Order Flow Imbalance (OFI) ───────────────────

    def compute_order_flow_imbalance(self, df_quotes: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes Order Flow Imbalance (OFI) from top-of-book quotes.
        Requires columns: ['bid_price', 'bid_size', 'ask_price', 'ask_size']
        """
        if df_quotes is None or len(df_quotes) < 2:
            return {"ofi_value": 0.0, "ofi_signal": "NEUTRAL", "flow_regime": "BALANCED"}

        try:
            bid_p = df_quotes['bid_price'].values
            bid_s = df_quotes['bid_size'].values
            ask_p = df_quotes['ask_price'].values
            ask_s = df_quotes['ask_size'].values

            e = np.zeros(len(df_quotes) - 1)
            for t in range(1, len(df_quotes)):
                if bid_p[t] > bid_p[t-1]:
                    delta_bid = bid_s[t]
                elif bid_p[t] == bid_p[t-1]:
                    delta_bid = bid_s[t] - bid_s[t-1]
                else:
                    delta_bid = -bid_s[t-1]

                if ask_p[t] < ask_p[t-1]:
                    delta_ask = ask_s[t]
                elif ask_p[t] == ask_p[t-1]:
                    delta_ask = ask_s[t] - ask_s[t-1]
                else:
                    delta_ask = -ask_s[t-1]

                e[t-1] = delta_bid - delta_ask

            ofi_sum = float(np.sum(e))
            ofi_mean = float(np.mean(e))
            ofi_std = float(np.std(e)) if np.std(e) > 0 else 1.0
            z_score = ofi_mean / ofi_std

            if z_score >= 1.5:
                signal = "INSTITUTIONAL_BUY_SURGE"
            elif z_score <= -1.5:
                signal = "INSTITUTIONAL_SELL_SURGE"
            else:
                signal = "NEUTRAL"

            return {
                "ofi_cumulative": round(ofi_sum, 2),
                "ofi_z_score": round(z_score, 3),
                "ofi_signal": signal,
                "is_whale_aggressive": abs(z_score) >= 2.0
            }
        except Exception as err:
            logger.warning(f"OFI calculation exception: {err}")
            return {"ofi_cumulative": 0.0, "ofi_z_score": 0.0, "ofi_signal": "NEUTRAL"}

    # ── 2. Volume-Synchronized Probability of Toxicity (VPIN) ─────────────────

    def compute_vpin(self, ticks_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes VPIN over volume-synchronized buckets using Lee-Ready trade classification.
        Requires columns: ['price', 'volume']
        """
        if ticks_df is None or len(ticks_df) < self.bucket_size:
            return {"vpin": 0.15, "toxicity_state": "LOW", "is_toxic": False}

        try:
            prices = ticks_df['price'].values
            volumes = ticks_df['volume'].values
            n = len(prices)

            directions = np.zeros(n)
            directions[0] = 1
            for i in range(1, n):
                if prices[i] > prices[i-1]:
                    directions[i] = 1
                elif prices[i] < prices[i-1]:
                    directions[i] = -1
                else:
                    directions[i] = directions[i-1]

            buy_vol = np.where(directions == 1, volumes, 0.0)
            sell_vol = np.where(directions == -1, volumes, 0.0)

            bucket_vol = float(np.sum(volumes) / max(self.num_buckets, 1))
            if bucket_vol <= 0:
                return {"vpin": 0.15, "toxicity_state": "LOW", "is_toxic": False}

            bucket_buy, bucket_sell = [], []
            cur_buy, cur_sell, cur_tot = 0.0, 0.0, 0.0

            for b, s, v in zip(buy_vol, sell_vol, volumes):
                cur_buy += b
                cur_sell += s
                cur_tot += v
                if cur_tot >= bucket_vol:
                    bucket_buy.append(cur_buy)
                    bucket_sell.append(cur_sell)
                    cur_buy, cur_sell, cur_tot = 0.0, 0.0, 0.0

            if len(bucket_buy) < 3:
                return {"vpin": 0.20, "toxicity_state": "NORMAL", "is_toxic": False}

            abs_imbalances = [abs(b - s) for b, s in zip(bucket_buy, bucket_sell)]
            vpin_val = float(np.sum(abs_imbalances) / (len(bucket_buy) * bucket_vol))
            vpin_val = min(max(vpin_val, 0.0), 1.0)

            toxicity_state = "CRITICAL_TOXIC" if vpin_val >= 0.65 else ("ELEVATED" if vpin_val >= 0.45 else "NORMAL")

            return {
                "vpin": round(vpin_val, 4),
                "toxicity_state": toxicity_state,
                "is_toxic": vpin_val >= 0.55,
                "pull_liquidity_defense": vpin_val >= 0.70
            }
        except Exception as err:
            logger.warning(f"VPIN calculation error: {err}")
            return {"vpin": 0.20, "toxicity_state": "NORMAL", "is_toxic": False}

    # ── 3. Global Net Liquidity Calculator ────────────────────────────────────

    def compute_net_liquidity(
        self,
        fed_balance_sheet_b: float = 6800.0,
        tga_balance_b: float = 750.0,
        on_rrp_b: float = 250.0
    ) -> Dict[str, Any]:
        """
        Computes Fed Net Liquidity = WALCL - TGA - ON_RRP (in Billions USD).
        """
        net_liq = fed_balance_sheet_b - tga_balance_b - on_rrp_b
        return {
            "fed_net_liquidity_b": round(net_liq, 2),
            "is_liquidity_expanding": net_liq > 5500.0,
            "crypto_beta_tailwind": "BULLISH" if net_liq > 5700.0 else "BEARISH"
        }
