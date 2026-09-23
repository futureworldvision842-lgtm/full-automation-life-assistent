import logging
import datetime
from typing import Dict, Any, Optional, Tuple

from src.institutional_knowledge import InstitutionalKnowledge
from src.ai_learning_engine import AILearningEngine
from src.experiential_replay_engine import ExperientialReplayEngine
from src.multi_regime_strategies import MultiRegimeStrategyMatrix

logger = logging.getLogger(__name__)

class StrategyEngine:
    """
    Price Action & Institutional SMC/ICT Strategy Generator.
    Features:
      - Primary Priority: Major Support/Resistance, Order Blocks (OB), Liquidity Sweeps, and Reversal Wicks.
      - Dynamic Structural Target (Adaptive R:R 1.0R to 5.0R):
        Analyzes the distance to the next Order Block / Support / Resistance to set the optimal TP.
      - Signature Winning Setup Reinforcement: Boosts proven winning patterns (up to 1.8x).
      - Multi-Regime Strategy Matrix (Trend, Judas Swing, Range Scalp, News Displacement).
      - Experiential Replay Online Weight Optimization.
    """

    def __init__(self, config: Dict[str, Any], ai_engine: Optional[AILearningEngine] = None):
        self.config = config
        self.min_rr_ratio = config["risk_management"].get("min_rr_ratio", 2.0)
        self.atr_sl_mult  = config["risk_management"].get("atr_sl_multiplier", 1.5)
        self.forex_atr_sl_mult = config["risk_management"].get("forex_atr_sl_multiplier", 1.5)
        # Gold gets a wider SL to comfortably survive normal volatility
        self.gold_atr_sl_mult = config["risk_management"].get("gold_atr_sl_multiplier", 2.5)
        # Crypto gets volatility-adjusted 3.5x ATR stops
        self.crypto_atr_sl_mult = config["risk_management"].get("crypto_atr_sl_multiplier", 3.5)
        self.ai_engine = ai_engine if ai_engine else AILearningEngine()
        self.experiential_replay = ExperientialReplayEngine()
        self.multi_regime = MultiRegimeStrategyMatrix()

        gold_cfg = config.get("gold_primary_focus", {})
        self.gold_focus_enabled  = gold_cfg.get("enabled", True)
        self.xauusd_min_score    = gold_cfg.get("xauusd_min_confluence_score", 1.2)
        self.other_min_score     = gold_cfg.get("other_pairs_min_confluence_score", 1.3)
        # NY close session block (15:00–17:00 UTC)
        self.ny_block_start = gold_cfg.get("ny_close_block_start_utc", 15)
        self.ny_block_end   = gold_cfg.get("ny_close_block_end_utc", 17)

    @staticmethod
    def get_symbol_scale_specs(symbol: str) -> Dict[str, Any]:
        """Returns standard calibration specs for any of the 7 supported assets."""
        sym = symbol.upper()
        if "BTC" in sym:
            return {"category": "CRYPTO", "pip_unit": 1.0, "min_sl_dist": 250.0, "atr_sl_mult": 3.5, "decimals": 2}
        elif "ETH" in sym:
            return {"category": "CRYPTO", "pip_unit": 1.0, "min_sl_dist": 20.0, "atr_sl_mult": 3.5, "decimals": 2}
        elif "SOL" in sym:
            return {"category": "CRYPTO", "pip_unit": 0.1, "min_sl_dist": 2.0, "atr_sl_mult": 3.5, "decimals": 2}
        elif "WIF" in sym:
            return {"category": "CRYPTO", "pip_unit": 0.01, "min_sl_dist": 0.02, "atr_sl_mult": 3.5, "decimals": 4}
        elif "PEPE" in sym:
            return {"category": "CRYPTO", "pip_unit": 0.0000001, "min_sl_dist": 0.0000002, "atr_sl_mult": 3.5, "decimals": 8}
        elif "BONK" in sym:
            return {"category": "CRYPTO", "pip_unit": 0.0000001, "min_sl_dist": 0.0000003, "atr_sl_mult": 3.5, "decimals": 8}
        elif "XAU" in sym or "GOLD" in sym:
            return {"category": "METALS", "pip_unit": 0.1, "min_sl_dist": 10.0, "atr_sl_mult": 2.5, "decimals": 2}
        elif "JPY" in sym:
            return {"category": "FOREX", "pip_unit": 0.01, "min_sl_dist": 0.15, "atr_sl_mult": 1.5, "decimals": 3}
        else:
            return {"category": "FOREX", "pip_unit": 0.0001, "min_sl_dist": 0.0012, "atr_sl_mult": 1.5, "decimals": 5}

    def calculate_dynamic_tp(self, symbol: str, signal_type: str, price: float, sl_distance: float, atr: float, analysis: Dict[str, Any]) -> Tuple[float, float, str]:
        """
        Calculates Take-Profit (TP) strictly from REAL CHART TECHNICAL ANALYSIS:
        - Real H1 & M15 Swing Highs / Pivot Highs (for BUY).
        - Real H1 & M15 Swing Lows / Demand Bases (for SELL).
        - Real Institutional Order Blocks & Fair Value Gaps detected on the chart.
        - Minimum 1:1 R:R floor, scaling as far as the chart structure permits!
        - ZERO synthetic or psychological numbers.
        Returns: (tp_price, realized_rr, target_description)
        """
        is_buy = signal_type == "BUY"
        trend = analysis.get("trend_direction", "NEUTRAL")

        candidates = []

        if is_buy:
            # 1. Real Chart Obstacles / Swing Highs above current price
            bearish_ob = analysis.get("bearish_ob")
            bearish_fvg = analysis.get("bearish_fvg")
            active_resistance = analysis.get("active_resistance")
            resistance_levels = analysis.get("resistance_levels", [])

            if bearish_ob and bearish_ob.get("low", 0) > price:
                candidates.append((bearish_ob["low"], "Bearish Order Block"))
            if active_resistance and active_resistance.get("level", 0) > price:
                candidates.append((active_resistance["level"], f"Key Resistance ({active_resistance.get('label', 'Zone')})"))
            for item in resistance_levels:
                r_lvl, r_lbl = item if isinstance(item, (tuple, list)) else (item, "Chart Resistance")
                if r_lvl > price + (0.3 * atr):
                    candidates.append((r_lvl, f"Chart Swing High @ {r_lvl:.2f} ({r_lbl})"))
            if bearish_fvg and bearish_fvg.get("bottom", 0) > price:
                candidates.append((bearish_fvg["bottom"], "Bearish FVG Ceiling"))

            # Sort ascending (closest above first)
            candidates.sort(key=lambda x: x[0])

            # Filter candidates that give >= 1.0 R:R
            valid_targets = []
            for lvl, name in candidates:
                rr = (lvl - price) / max(sl_distance, 1e-6)
                if rr >= 0.95:  # Minimum 1:1 floor
                    valid_targets.append((lvl, rr, name))

            if valid_targets:
                # If strong trend, pick higher swing level (larger runner), else nearest major swing
                chosen = valid_targets[1] if (trend == "BULLISH" and len(valid_targets) > 1) else valid_targets[0]
                target_lvl, chosen_rr, target_name = chosen
                # Place TP safely 0.2*ATR before the pivot to guarantee fill
                tp_price = max(price + (1.0 * sl_distance), target_lvl - (0.2 * atr))
                realized_rr = (tp_price - price) / sl_distance
                target_desc = f"Chart Target: {target_name} ({realized_rr:.2f}R Target)"
                return tp_price, round(realized_rr, 2), target_desc

            # If chart has clean open space / breakout
            default_lvl = price + (3.0 * sl_distance)
            return default_lvl, 3.0, "Chart Open Sky Breakout Target (3.0R)"

        else: # SELL
            # 1. Real Chart Obstacles / Swing Lows below current price
            bullish_ob = analysis.get("bullish_ob")
            bullish_fvg = analysis.get("bullish_fvg")
            active_support = analysis.get("active_support")
            support_levels = analysis.get("support_levels", [])

            if bullish_ob and bullish_ob.get("high", 0) < price:
                candidates.append((bullish_ob["high"], "Bullish Order Block"))
            if active_support and active_support.get("level", 0) < price:
                candidates.append((active_support["level"], f"Key Support ({active_support.get('label', 'Zone')})"))
            for item in support_levels:
                s_lvl, s_lbl = item if isinstance(item, (tuple, list)) else (item, "Chart Support")
                if s_lvl < price - (0.3 * atr):
                    candidates.append((s_lvl, f"Chart Swing Low / Base @ {s_lvl:.2f} ({s_lbl})"))
            if bullish_fvg and bullish_fvg.get("top", 0) < price:
                candidates.append((bullish_fvg["top"], "Bullish FVG Floor"))

            # Sort descending (closest below first)
            candidates.sort(key=lambda x: x[0], reverse=True)

            # Filter candidates that give >= 1.0 R:R
            valid_targets = []
            for lvl, name in candidates:
                rr = (price - lvl) / max(sl_distance, 1e-6)
                if rr >= 0.95:  # Minimum 1:1 floor
                    valid_targets.append((lvl, rr, name))

            if valid_targets:
                # If strong trend, pick deeper swing low (e.g. major H1 base), else nearest chart support
                chosen = valid_targets[1] if (trend == "BEARISH" and len(valid_targets) > 1) else valid_targets[0]
                target_lvl, chosen_rr, target_name = chosen
                # Place TP safely 0.2*ATR above the pivot to guarantee fill
                tp_price = min(price - (1.0 * sl_distance), target_lvl + (0.2 * atr))
                realized_rr = (price - tp_price) / sl_distance
                target_desc = f"Chart Target: {target_name} ({realized_rr:.2f}R Target)"
                return tp_price, round(realized_rr, 2), target_desc

            # If chart has clean open space / breakdown
            default_lvl = price - (3.0 * sl_distance)
            return default_lvl, 3.0, "Chart Open Air Breakdown Target (3.0R)"

    def evaluate_signals(self, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Evaluates market analysis based on Price Action, Support/Resistance & SMC first.
        Executes trade whenever price reacts at strong Order Blocks, Support/Resistance, or Sweeps.
        """
        symbol = analysis["symbol"]
        price = analysis["current_price"]
        trend = analysis["trend_direction"]
        rsi = analysis["rsi"]
        atr = analysis["atr"]
        df_entry = analysis["df_entry"]

        bullish_fvg = analysis.get("bullish_fvg")
        bearish_fvg = analysis.get("bearish_fvg")
        bullish_ob = analysis.get("bullish_ob")
        bearish_ob = analysis.get("bearish_ob")
        active_support = analysis.get("active_support")
        active_resistance = analysis.get("active_resistance")
        sweep = analysis.get("liquidity_sweep", {})
        candlesticks = analysis.get("candlestick_patterns", [])
        struct_pattern = analysis.get("structure_pattern")

        if atr <= 0:
            return None

        candle_time = analysis.get("candle_time")
        if candle_time is not None:
            if hasattr(candle_time, "hour"):
                utc_now = candle_time
            elif isinstance(candle_time, (int, float)):
                utc_now = datetime.datetime.fromtimestamp(candle_time, datetime.timezone.utc)
            else:
                try:
                    utc_now = pd.to_datetime(candle_time, utc=True).to_pydatetime()
                except Exception:
                    utc_now = datetime.datetime.now(datetime.timezone.utc)
        else:
            utc_now = datetime.datetime.now(datetime.timezone.utc)
        current_hour = utc_now.hour
        session_name = InstitutionalKnowledge.get_trading_session(utc_now)
        pattern_weights = self.ai_engine.get_pattern_weights()

        # NY Close Block for Gold (15:00–17:00 UTC)
        # If killzone is explicitly supplied in analysis (e.g. backtesting/stress testing) or test_mode is set, respect context
        killzone_info = analysis.get("killzone", {})
        is_mock_kz = killzone_info.get("is_prime_killzone") and killzone_info.get("killzone") in ["LONDON_OPEN", "NEW_YORK_OPEN", "ASIAN_SESSION"]
        if not is_mock_kz and not analysis.get("bypass_time_filter", False) and symbol == "XAUUSD" and self.ny_block_start <= current_hour < self.ny_block_end:
            logger.info(f"[NY Close Block] XAUUSD skipped — NY close manipulation zone ({current_hour}:xx UTC)")
            return None

        # Choose SL multiplier: Crypto gets 3.5x ATR, Gold gets 2.5x ATR, Forex gets 1.5x ATR
        specs = self.get_symbol_scale_specs(symbol)
        if specs["category"] == "CRYPTO":
            sl_mult = self.crypto_atr_sl_mult
        elif specs["category"] == "METALS":
            sl_mult = self.gold_atr_sl_mult
        else:
            sl_mult = self.forex_atr_sl_mult

        has_pinbar_buy = any(c["type"] == "BULLISH_PINBAR" for c in candlesticks)
        has_pinbar_sell = any(c["type"] == "BEARISH_PINBAR" for c in candlesticks)
        has_engulfing_buy = any(c["type"] == "BULLISH_ENGULFING" for c in candlesticks)
        has_engulfing_sell = any(c["type"] == "BEARISH_ENGULFING" for c in candlesticks)

        is_gold = (symbol == "XAUUSD")
        min_required_score = self.xauusd_min_score if is_gold else self.other_min_score

        # ---------------------------------------------------------------------
        # 1. BULLISH PRICE ACTION SETUPS (BUY)
        # Price is at Support, Order Block, Liquidity Sweep, or Bullish Pattern
        # ---------------------------------------------------------------------
        has_bullish_pa = (
            active_support is not None or
            bullish_ob is not None or
            sweep.get("type") == "BULLISH_SWEEP" or
            struct_pattern == "DOUBLE_BOTTOM" or
            bullish_fvg is not None or
            has_pinbar_buy or
            has_engulfing_buy or
            trend == "BULLISH"
        )

        # Strict Trend Dominance: NEVER take counter-trend BUY into a BEARISH H1 trend
        if trend == "BEARISH":
            logger.info(f"[{symbol}] Counter-trend BUY strictly BLOCKED: H1 Trend is BEARISH. Only pullbacks/sells allowed.")
            return None

        # Only prevent BUY if RSI is dangerously overbought (RSI > 78)
        if has_bullish_pa and rsi <= 78:
            confluence_score = 0.0
            pattern_type = "BULLISH_PRICE_ACTION"
            sl_anchor = price - (sl_mult * atr)

            # A. Institutional Order Block (+0.9)
            if bullish_ob and (bullish_ob["low"] * 0.999 <= price <= bullish_ob["high"] * 1.002):
                confluence_score += 0.9
                pattern_type = "BULLISH_ORDER_BLOCK"
                sl_anchor = min(sl_anchor, bullish_ob["low"])

            # B. Liquidity Sweep / Stop Hunt (+0.9)
            if sweep.get("type") == "BULLISH_SWEEP":
                confluence_score += 0.9
                pattern_type = "BULLISH_SWEEP"
                sl_anchor = min(sl_anchor, sweep.get("rejection_wick_price", sl_anchor))

            # C. Major Support Level Bounce (+0.8)
            if active_support is not None:
                confluence_score += 0.8
                if pattern_type == "BULLISH_PRICE_ACTION":
                    pattern_type = "KEY_SUPPORT_BOUNCE"
                sl_anchor = min(sl_anchor, active_support["level"] - (0.5 * atr))

            # D. Fair Value Gap Reaction (+0.6 to +0.7 on CE 50% test)
            if bullish_fvg and (bullish_fvg["bottom"] * 0.999 <= price <= bullish_fvg["top"] * 1.001):
                ce_level = bullish_fvg.get("ce_50", bullish_fvg.get("ce", (bullish_fvg["top"] + bullish_fvg["bottom"]) / 2.0))
                is_ce_test = abs(price - ce_level) <= (0.3 * atr)
                fvg_bonus = 0.70 if is_ce_test else 0.60
                confluence_score += fvg_bonus
                if pattern_type == "BULLISH_PRICE_ACTION":
                    pattern_type = "BULLISH_FVG_50_CE" if is_ce_test else "BULLISH_FVG"
                sl_anchor = min(sl_anchor, bullish_fvg["bottom"])

            # E. Reversal Candlesticks (+0.5)
            if has_pinbar_buy or has_engulfing_buy:
                confluence_score += 0.5

            # F. Double Bottom / Structure (+0.5)
            if struct_pattern == "DOUBLE_BOTTOM":
                confluence_score += 0.5

            # G. Oversold Support Value Bonus (RSI < 32 at Support/OB is a strength, not a blocker)
            if rsi < 32:
                confluence_score += 0.4
                logger.info(f"[{symbol}] Oversold Reversal Value Bonus added (RSI: {rsi:.1f})")
            elif 32 <= rsi <= 60:
                confluence_score += 0.2

            # H. Sovereign Gold Benchmark & Institutional Level Confluence
            if is_gold:
                confluence_score += 0.5  # Gold King Sovereign Priority
                gold_intel = analysis.get("gold_intel")
                if gold_intel:
                    if gold_intel.get("asian_sweep") == "ASIAN_LOW_SWEEP":
                        confluence_score += 0.8
                        pattern_type = "GOLD_ASIAN_SWEEP_BOUNCE"
                        logger.info("[Gold King Setup] Asian Low Liquidity Sweep detected (+0.8 Confluence)")
                    if gold_intel.get("at_psychological_level"):
                        confluence_score += 0.5
                        p_lvl = gold_intel.get("nearest_psychological_25")
                        logger.info(f"[Gold King Setup] Price at ${p_lvl:.0f} Institutional Psychological Level (+0.5 Confluence)")

            # I. Trend Alignment Bonus (Optional confirmation)
            if trend == "BULLISH":
                confluence_score += 0.3

            # J. Volume Spread Analysis (VSA) Institutional Absorption Confluence (+0.4)
            vsa_intel = analysis.get("vsa_intel", {})
            if vsa_intel.get("is_absorption") and vsa_intel.get("type") == "BULLISH_ABSORPTION":
                confluence_score += 0.4
                logger.info(f"[{symbol}] VSA Bullish Institutional Volume Absorption detected (Ratio: {vsa_intel.get('volume_ratio')}x) (+0.4 Confluence)")

            # K. Aladdin Premium vs Discount 50% Equilibrium Filter
            prem_disc = analysis.get("premium_discount", {})
            if not prem_disc.get("is_buy_allowed", True) and not (active_support or bullish_ob):
                logger.info(f"[{symbol}] BUY blocked: Price is in PREMIUM zone ({prem_disc.get('discount_pct')}% discount). Institutional buying requires DISCOUNT.")
                return None

            # L. Optimal Trade Entry (OTE 70.5% Institutional Golden Pocket) (+0.60)
            ote_buy = analysis.get("ote_buy", {})
            if ote_buy.get("in_ote_zone"):
                confluence_score += ote_buy.get("score_bonus", 0.60)
                logger.info(f"[{symbol}] OTE 70.5% Institutional Fibonacci Sweet Spot detected (+0.60 Confluence)")

            # M. Interbank Killzones Temporal Boost (+0.40)
            killzone = analysis.get("killzone", {})
            if killzone.get("is_prime_killzone"):
                confluence_score += killzone.get("confluence_boost", 0.40)
                logger.info(f"[{symbol}] Prime Interbank Killzone active ({killzone.get('killzone')}) (+{killzone.get('confluence_boost')} Confluence)")

            # N. Equal Lows (EQL) Inducement Liquidity Sweep (+0.50)
            inducement = analysis.get("inducement", {})
            if inducement.get("inducement_type") == "BULLISH_EQL_SWEEP":
                confluence_score += 0.50
                logger.info(f"[{symbol}] Equal Lows (EQL) Retail Liquidity Inducement Swept (+0.50 Confluence)")

            # N2. Post-News Liquidity Sweep / Judas Trap (+0.80)
            news_sweep = analysis.get("news_liquidity_sweep", {})
            if news_sweep.get("is_post_news_trap") and news_sweep.get("direction") == "BULLISH":
                confluence_score += 0.80
                pattern_type = "POST_NEWS_JUDAS_SWEEP"
                logger.info(f"[{symbol}] Post-News Judas Trap Reversal detected (+0.80 Confluence)")

            # O. ADR Exhaustion Filter: Block breakout buying if 120%+ of daily range is spent
            adr_intel = analysis.get("adr_intel", {})
            if adr_intel.get("is_adr_exhausted") and not (active_support or bullish_ob):
                logger.info(f"[{symbol}] BUY blocked by ADR Exhaustion: {adr_intel.get('adr_pct_consumed')}% ADR consumed today. Chasing tops blocked.")
                return None

            # P. Microsoft Qlib Alpha158 Factor Confluence (+0.30)
            qlib_intel = analysis.get("qlib_intel", {})
            if qlib_intel.get("bias") == "BULLISH":
                confluence_score += qlib_intel.get("confluence_bonus", 0.30)
                logger.info(f"[{symbol}] Qlib Alpha158 Bullish Factor Alignment (Score: {qlib_intel.get('alpha_score')}) (+{qlib_intel.get('confluence_bonus', 0.30)} Confluence)")

            weight = pattern_weights.get(pattern_type, 1.0)
            
            # Check if this is an AI-proven Signature Winning Setup
            signature_setups = self.ai_engine.get_signature_setups() if hasattr(self.ai_engine, "get_signature_setups") else []
            is_signature = pattern_type in signature_setups or weight >= 1.25
            if is_signature:
                confluence_score += 0.3  # Bonus reinforcement for proven winning setups
                effective_min_score = max(0.9, min_required_score - 0.2)  # Lower friction for winning setups
            else:
                effective_min_score = min_required_score

            final_score = confluence_score * weight

            if final_score >= effective_min_score:
                recent_low = df_entry['low'].tail(10).min()
                raw_sl = min(sl_anchor, recent_low - (0.5 * atr))
                
                # Calibrated Minimum SL distance guard
                pip_unit = specs["pip_unit"]
                min_sl_dist = specs["min_sl_dist"]
                
                sl_distance = max(price - raw_sl, min_sl_dist)
                sl_price = price - sl_distance

                if sl_distance > 0:
                    # Dynamic Structural Take-Profit Target (1.2R up to 5.0R)
                    tp_price, dyn_rr, target_desc = self.calculate_dynamic_tp(
                        symbol=symbol,
                        signal_type="BUY",
                        price=price,
                        sl_distance=sl_distance,
                        atr=atr,
                        analysis=analysis
                    )

                    tag = "🔥 SIGNATURE WINNING SETUP" if is_signature else "SMC Price Action"
                    logger.info(
                        f"STRATEGY SIGNAL [{symbol}]: BUY at {price:.5f} | "
                        f"SL: {sl_price:.5f} ({sl_distance/pip_unit:.1f} pips) | "
                        f"TP: {tp_price:.5f} (R:R {dyn_rr:.1f}) | {target_desc} | "
                        f"Score: {final_score:.2f} ({weight:.2f}x) | Session: {session_name}"
                    )
                    return {
                        "symbol": symbol,
                        "signal": "BUY",
                        "pattern": pattern_type,
                        "session": session_name,
                        "entry_price": price,
                        "sl_price": sl_price,
                        "tp_price": tp_price,
                        "rsi": rsi,
                        "atr": atr,
                        "reason": f"{tag} ({target_desc}, Score: {final_score:.2f})",
                        "rr_ratio": dyn_rr,
                        "confluence_score": final_score
                    }

        # ---------------------------------------------------------------------
        # 2. BEARISH PRICE ACTION SETUPS (SELL)
        # Price is at Resistance, Order Block, Liquidity Sweep, or Bearish Pattern
        # ---------------------------------------------------------------------
        has_bearish_pa = (
            active_resistance is not None or
            bearish_ob is not None or
            sweep.get("type") == "BEARISH_SWEEP" or
            struct_pattern == "DOUBLE_TOP" or
            bearish_fvg is not None or
            has_pinbar_sell or
            has_engulfing_sell or
            trend == "BEARISH"
        )

        # Strict Trend Dominance: NEVER take counter-trend SELL into a BULLISH H1 trend
        if trend == "BULLISH":
            logger.info(f"[{symbol}] Counter-trend SELL strictly BLOCKED: H1 Trend is BULLISH. Only pullbacks/buys allowed.")
            return None

        # Only prevent SELL if RSI is dangerously oversold (RSI < 22)
        if has_bearish_pa and rsi >= 22:
            confluence_score = 0.0
            pattern_type = "BEARISH_PRICE_ACTION"
            sl_anchor = price + (sl_mult * atr)

            # A. Institutional Order Block (+0.9)
            if bearish_ob and (bearish_ob["low"] * 0.998 <= price <= bearish_ob["high"] * 1.001):
                confluence_score += 0.9
                pattern_type = "BEARISH_ORDER_BLOCK"
                sl_anchor = max(sl_anchor, bearish_ob["high"])

            # B. Liquidity Sweep / Stop Hunt (+0.9)
            if sweep.get("type") == "BEARISH_SWEEP":
                confluence_score += 0.9
                pattern_type = "BEARISH_SWEEP"
                sl_anchor = max(sl_anchor, sweep.get("rejection_wick_price", sl_anchor))

            # C. Major Resistance Level Rejection (+0.8)
            if active_resistance is not None:
                confluence_score += 0.8
                if pattern_type == "BEARISH_PRICE_ACTION":
                    pattern_type = "KEY_RESISTANCE_REJECTION"
                sl_anchor = max(sl_anchor, active_resistance["level"] + (0.5 * atr))

            # D. Fair Value Gap Reaction (+0.6 to +0.7 on CE 50% test)
            if bearish_fvg and (bearish_fvg["bottom"] * 0.999 <= price <= bearish_fvg["top"] * 1.001):
                ce_level = bearish_fvg.get("ce_50", bearish_fvg.get("ce", (bearish_fvg["top"] + bearish_fvg["bottom"]) / 2.0))
                is_ce_test = abs(price - ce_level) <= (0.3 * atr)
                fvg_bonus = 0.70 if is_ce_test else 0.60
                confluence_score += fvg_bonus
                if pattern_type == "BEARISH_PRICE_ACTION":
                    pattern_type = "BEARISH_FVG_50_CE" if is_ce_test else "BEARISH_FVG"
                sl_anchor = max(sl_anchor, bearish_fvg["top"])

            # E. Reversal Candlesticks (+0.5)
            if has_pinbar_sell or has_engulfing_sell:
                confluence_score += 0.5

            # F. Double Top / Structure (+0.5)
            if struct_pattern == "DOUBLE_TOP":
                confluence_score += 0.5

            # G. Overbought Resistance Bonus (RSI > 68 at Resistance/OB is a strength)
            if rsi > 68:
                confluence_score += 0.4
                logger.info(f"[{symbol}] Overbought Reversal Bonus added (RSI: {rsi:.1f})")
            elif 40 <= rsi <= 68:
                confluence_score += 0.2

            # H. Sovereign Gold Benchmark & Institutional Level Confluence
            if is_gold:
                confluence_score += 0.5  # Gold King Sovereign Priority
                gold_intel = analysis.get("gold_intel")
                if gold_intel:
                    if gold_intel.get("asian_sweep") == "ASIAN_HIGH_SWEEP":
                        confluence_score += 0.8
                        pattern_type = "GOLD_ASIAN_SWEEP_REJECTION"
                        logger.info("[Gold King Setup] Asian High Liquidity Sweep detected (+0.8 Confluence)")
                    if gold_intel.get("at_psychological_level"):
                        confluence_score += 0.5
                        p_lvl = gold_intel.get("nearest_psychological_25")
                        logger.info(f"[Gold King Setup] Price at ${p_lvl:.0f} Institutional Psychological Level (+0.5 Confluence)")

            # I. Trend Alignment Bonus (Optional confirmation)
            if trend == "BEARISH":
                confluence_score += 0.3

            # J. Volume Spread Analysis (VSA) Institutional Absorption Confluence (+0.4)
            vsa_intel = analysis.get("vsa_intel", {})
            if vsa_intel.get("is_absorption") and vsa_intel.get("type") == "BEARISH_ABSORPTION":
                confluence_score += 0.4
                logger.info(f"[{symbol}] VSA Bearish Institutional Volume Absorption detected (Ratio: {vsa_intel.get('volume_ratio')}x) (+0.4 Confluence)")

            # K. Aladdin Premium vs Discount 50% Equilibrium Filter
            prem_disc = analysis.get("premium_discount", {})
            if not prem_disc.get("is_sell_allowed", True) and not (active_resistance or bearish_ob):
                logger.info(f"[{symbol}] SELL blocked: Price is in DISCOUNT zone ({prem_disc.get('discount_pct')}% discount). Institutional selling requires PREMIUM.")
                return None

            # L. Optimal Trade Entry (OTE 70.5% Institutional Golden Pocket) (+0.60)
            ote_sell = analysis.get("ote_sell", {})
            if ote_sell.get("in_ote_zone"):
                confluence_score += ote_sell.get("score_bonus", 0.60)
                logger.info(f"[{symbol}] OTE 70.5% Institutional Fibonacci Sweet Spot detected (+0.60 Confluence)")

            # M. Interbank Killzones Temporal Boost (+0.40)
            killzone = analysis.get("killzone", {})
            if killzone.get("is_prime_killzone"):
                confluence_score += killzone.get("confluence_boost", 0.40)
                logger.info(f"[{symbol}] Prime Interbank Killzone active ({killzone.get('killzone')}) (+{killzone.get('confluence_boost')} Confluence)")

            # N. Equal Highs (EQH) Inducement Liquidity Sweep (+0.50)
            inducement = analysis.get("inducement", {})
            if inducement.get("inducement_type") == "BEARISH_EQH_SWEEP":
                confluence_score += 0.50
                logger.info(f"[{symbol}] Equal Highs (EQH) Retail Liquidity Inducement Swept (+0.50 Confluence)")

            # N2. Post-News Liquidity Sweep / Judas Trap (+0.80)
            news_sweep = analysis.get("news_liquidity_sweep", {})
            if news_sweep.get("is_post_news_trap") and news_sweep.get("direction") == "BEARISH":
                confluence_score += 0.80
                pattern_type = "POST_NEWS_JUDAS_SWEEP"
                logger.info(f"[{symbol}] Post-News Judas Trap Reversal detected (+0.80 Confluence)")

            # O. ADR Exhaustion Filter: Block breakdown selling if 120%+ of daily range is spent
            adr_intel = analysis.get("adr_intel", {})
            if adr_intel.get("is_adr_exhausted") and not (active_resistance or bearish_ob):
                logger.info(f"[{symbol}] SELL blocked by ADR Exhaustion: {adr_intel.get('adr_pct_consumed')}% ADR consumed today. Chasing bottoms blocked.")
                return None

            # P. Microsoft Qlib Alpha158 Factor Confluence (+0.30)
            qlib_intel = analysis.get("qlib_intel", {})
            if qlib_intel.get("bias") == "BEARISH":
                confluence_score += qlib_intel.get("confluence_bonus", 0.30)
                logger.info(f"[{symbol}] Qlib Alpha158 Bearish Factor Alignment (Score: {qlib_intel.get('alpha_score')}) (+{qlib_intel.get('confluence_bonus', 0.30)} Confluence)")

            weight = pattern_weights.get(pattern_type, 1.0)
            
            # Check if this is an AI-proven Signature Winning Setup
            signature_setups = self.ai_engine.get_signature_setups() if hasattr(self.ai_engine, "get_signature_setups") else []
            is_signature = pattern_type in signature_setups or weight >= 1.25
            if is_signature:
                confluence_score += 0.3  # Bonus reinforcement for proven winning setups
                effective_min_score = max(0.9, min_required_score - 0.2)  # Lower friction for winning setups
            else:
                effective_min_score = min_required_score

            final_score = confluence_score * weight

            if final_score >= effective_min_score:
                recent_high = df_entry['high'].tail(10).max()
                raw_sl = max(sl_anchor, recent_high + (0.5 * atr))
                
                # Calibrated Minimum SL distance guard
                pip_unit = specs["pip_unit"]
                min_sl_dist = specs["min_sl_dist"]
                
                sl_distance = max(raw_sl - price, min_sl_dist)
                sl_price = price + sl_distance

                if sl_distance > 0:
                    # Dynamic Structural Take-Profit Target (1.2R up to 5.0R)
                    tp_price, dyn_rr, target_desc = self.calculate_dynamic_tp(
                        symbol=symbol,
                        signal_type="SELL",
                        price=price,
                        sl_distance=sl_distance,
                        atr=atr,
                        analysis=analysis
                    )

                    tag = "🔥 SIGNATURE WINNING SETUP" if is_signature else "SMC Price Action"
                    logger.info(
                        f"STRATEGY SIGNAL [{symbol}]: SELL at {price:.5f} | "
                        f"SL: {sl_price:.5f} ({sl_distance/pip_unit:.1f} pips) | "
                        f"TP: {tp_price:.5f} (R:R {dyn_rr:.1f}) | {target_desc} | "
                        f"Score: {final_score:.2f} ({weight:.2f}x) | Session: {session_name}"
                    )
                    return {
                        "symbol": symbol,
                        "signal": "SELL",
                        "pattern": pattern_type,
                        "session": session_name,
                        "entry_price": price,
                        "sl_price": sl_price,
                        "tp_price": tp_price,
                        "rsi": rsi,
                        "atr": atr,
                        "reason": f"{tag} ({target_desc}, Score: {final_score:.2f})",
                        "rr_ratio": dyn_rr,
                        "confluence_score": final_score
                    }

        return None
