import logging
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import numpy as np

from src.market_maker_game_engine import MarketMakerGameEngine
from src.chart_pattern_engine import ChartPatternEngine
from src.predictive_weather_engine import PredictiveWeatherEngine
from src.fincept_terminal_intel import FinceptTerminalIntel
from src.order_flow_quant import OrderFlowQuantEngine
from src.aladdin_regime_model import QuantitativeRegimeDetector
from src.qlib_alpha158_engine import QlibAlpha158Engine
from src.intermarket_macro_radar import IntermarketMacroRadar
from src.economic_calendar_radar import EconomicCalendarRadar
from src.insider_whale_mechanics import InsiderWhaleMechanics
from src.market_history_encyclopedia import MarketHistoryEncyclopedia
from src.cross_market_synthetic_arb import CrossMarketContagionEngine
from src.trend_confluence_filter import MultiTimeframeConfluenceFilter

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    """
    Institutional Technical, SMC/ICT, Market Maker Game, Fincept Terminal, Aladdin Quant & Satellite Weather Analyzer.
    Detects Fair Value Gaps (FVG), Order Blocks (OB), Major Support/Resistance Levels,
    Liquidity Sweeps, ICT Judas Swings, Pinbars, Double Tops/Bottoms, OTE Arrays, Lee-Ready CVD, Qlib Alpha158,
    Inter-Market Radar, Insider Whale Shocks, 50-Year History Analogues, and Statistical Regimes.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mm_game = MarketMakerGameEngine()
        self.chart_patterns = ChartPatternEngine()
        self.weather_engine = PredictiveWeatherEngine()
        self.fincept_intel = FinceptTerminalIntel()
        self.order_flow_quant = OrderFlowQuantEngine()
        self.regime_detector = QuantitativeRegimeDetector()
        self.qlib_engine = QlibAlpha158Engine()
        self.intermarket_radar = IntermarketMacroRadar()
        self.calendar_radar = EconomicCalendarRadar()
        self.insider_whales = InsiderWhaleMechanics()
        self.history_encyclopedia = MarketHistoryEncyclopedia()
        self.cross_market = CrossMarketContagionEngine()
        self.confluence_filter = MultiTimeframeConfluenceFilter()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Computes technical indicators, ATR, RSI, MACD, and Fincept Terminal metrics."""
        df = df.copy()

        # Moving Averages
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # Relative Strength Index (RSI 14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['rsi'] = 100 - (100 / (1 + rs))

        # Average True Range (ATR 14)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(window=14).mean()

        # Fincept Terminal Indicators (MACD, Bollinger Bands, Sentiment Index)
        df = self.fincept_intel.calculate_fincept_indicators(df)

        return df

    @staticmethod
    def detect_fvg(df: pd.DataFrame, min_gap_pips: float = 2.0, symbol: str = "EURUSD") -> List[Dict[str, Any]]:
        """
        Detects Bullish and Bearish Fair Value Gaps (FVG) with 50% Consequent Encroachment (CE 50%)
        and multi-candle forward mitigation state tracking.
        """
        fvgs = []
        if df is None or len(df) < 3:
            return fvgs

        sym = symbol.upper()
        if "BTC" in sym or "ETH" in sym:
            pip_unit = 1.0
        elif "SOL" in sym or "XAU" in sym or "GOLD" in sym:
            pip_unit = 0.1
        elif "JPY" in sym or "WIF" in sym:
            pip_unit = 0.01
        elif "PEPE" in sym or "BONK" in sym:
            pip_unit = 0.0000001
        else:
            pip_unit = 0.0001

        n = len(df)
        for i in range(2, n):
            c1_high = df['high'].iloc[i - 2]
            c1_low = df['low'].iloc[i - 2]
            c3_high = df['high'].iloc[i]
            c3_low = df['low'].iloc[i]

            if c3_low > c1_high:
                gap_size = (c3_low - c1_high) / pip_unit
                if gap_size >= min_gap_pips:
                    top = float(c3_low)
                    bottom = float(c1_high)
                    ce = (top + bottom) / 2.0

                    # Forward mitigation tracking across future bars
                    mitigated = False
                    partially_mitigated = False
                    if i + 1 < n:
                        future_lows = df['low'].iloc[i+1:].values
                        if len(future_lows) > 0:
                            min_future_low = float(np.min(future_lows))
                            if min_future_low <= ce:
                                mitigated = True
                                partially_mitigated = True
                            elif min_future_low <= top:
                                partially_mitigated = True

                    fvgs.append({
                        "type": "BULLISH_FVG",
                        "index": i,
                        "time": df['time'].iloc[i] if 'time' in df.columns else i,
                        "top": top,
                        "bottom": bottom,
                        "ce": ce,
                        "ce_50": ce,
                        "gap_pips": gap_size,
                        "mitigated": mitigated,
                        "partially_mitigated": partially_mitigated
                    })
            elif c3_high < c1_low:
                gap_size = (c1_low - c3_high) / pip_unit
                if gap_size >= min_gap_pips:
                    top = float(c1_low)
                    bottom = float(c3_high)
                    ce = (top + bottom) / 2.0

                    # Forward mitigation tracking across future bars
                    mitigated = False
                    partially_mitigated = False
                    if i + 1 < n:
                        future_highs = df['high'].iloc[i+1:].values
                        if len(future_highs) > 0:
                            max_future_high = float(np.max(future_highs))
                            if max_future_high >= ce:
                                mitigated = True
                                partially_mitigated = True
                            elif max_future_high >= bottom:
                                partially_mitigated = True

                    fvgs.append({
                        "type": "BEARISH_FVG",
                        "index": i,
                        "time": df['time'].iloc[i] if 'time' in df.columns else i,
                        "top": top,
                        "bottom": bottom,
                        "ce": ce,
                        "ce_50": ce,
                        "gap_pips": gap_size,
                        "mitigated": mitigated,
                        "partially_mitigated": partially_mitigated
                    })

        return fvgs

    @staticmethod
    def detect_order_blocks(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identifies Institutional Order Blocks (OB)."""
        order_blocks = []
        if df is None or len(df) < 4:
            return order_blocks

        for i in range(0, len(df) - 2):
            prev_candle = df.iloc[i]
            next_candle_1 = df.iloc[i + 1]
            next_candle_2 = df.iloc[i + 2]

            if prev_candle['close'] < prev_candle['open']:
                if next_candle_1['close'] > next_candle_1['open'] and next_candle_2['close'] > next_candle_2['open']:
                    if next_candle_2['close'] > prev_candle['high']:
                        order_blocks.append({
                            "type": "BULLISH_OB",
                            "time": prev_candle['time'],
                            "high": prev_candle['high'],
                            "low": prev_candle['low'],
                            "entry_price": prev_candle['high'],
                            "sl_price": prev_candle['low']
                        })
            elif prev_candle['close'] > prev_candle['open']:
                if next_candle_1['close'] < next_candle_1['open'] and next_candle_2['close'] < next_candle_2['open']:
                    if next_candle_2['close'] < prev_candle['low']:
                        order_blocks.append({
                            "type": "BEARISH_OB",
                            "time": prev_candle['time'],
                            "high": prev_candle['high'],
                            "low": prev_candle['low'],
                            "entry_price": prev_candle['low'],
                            "sl_price": prev_candle['high']
                        })

        return order_blocks

    @staticmethod
    def detect_key_support_resistance(df_trend: pd.DataFrame, df_entry: pd.DataFrame, current_price: float, atr: float, symbol: str) -> Dict[str, Any]:
        """
        Detects Major Structural Support and Resistance levels directly from REAL H1 & M15 chart candles.
        Extracts genuine pivot swing highs and swing lows without synthetic calculations.
        """
        sym = symbol.upper()
        if "BTC" in sym or "ETH" in sym or "SOL" in sym or any(m in sym for m in ["PEPE", "BONK", "WIF"]):
            threshold = 2.5 * atr
        elif "XAU" in sym or "GOLD" in sym:
            threshold = 2.0 * atr
        else:
            threshold = 1.2 * atr

        # 1. Extract H1 Major Chart Swings (Trend Timeframe - last 100 candles)
        h1_lows = df_trend['low'].values
        h1_highs = df_trend['high'].values
        h1_support = []
        h1_resistance = []

        for i in range(2, len(h1_lows) - 2):
            if h1_lows[i] <= h1_lows[i-1] and h1_lows[i] <= h1_lows[i-2] and h1_lows[i] <= h1_lows[i+1] and h1_lows[i] <= h1_lows[i+2]:
                h1_support.append((float(h1_lows[i]), "H1 Major Swing Low"))
            if h1_highs[i] >= h1_highs[i-1] and h1_highs[i] >= h1_highs[i-2] and h1_highs[i] >= h1_highs[i+1] and h1_highs[i] >= h1_highs[i+2]:
                h1_resistance.append((float(h1_highs[i]), "H1 Major Swing High"))

        # 2. Extract M15 Chart Swings (Entry Timeframe - last 60 candles)
        m15_lows = df_entry['low'].values
        m15_highs = df_entry['high'].values
        m15_support = []
        m15_resistance = []

        for i in range(2, len(m15_lows) - 2):
            if m15_lows[i] <= m15_lows[i-1] and m15_lows[i] <= m15_lows[i-2] and m15_lows[i] <= m15_lows[i+1] and m15_lows[i] <= m15_lows[i+2]:
                m15_support.append((float(m15_lows[i]), "M15 Chart Support"))
            if m15_highs[i] >= m15_highs[i-1] and m15_highs[i] >= m15_highs[i-2] and m15_highs[i] >= m15_highs[i+1] and m15_highs[i] >= m15_highs[i+2]:
                m15_resistance.append((float(m15_highs[i]), "M15 Chart Resistance"))

        # Combine and deduplicate
        all_supports = h1_support + m15_support
        all_resistances = h1_resistance + m15_resistance

        # Sort supports descending (closest below first)
        all_supports.sort(key=lambda x: x[0], reverse=True)
        # Sort resistances ascending (closest above first)
        all_resistances.sort(key=lambda x: x[0])

        # Active Support Check
        active_support = None
        min_supp_dist = float('inf')
        for s, label in all_supports:
            dist = abs(current_price - s)
            if dist < threshold and current_price >= (s - (0.5 * atr)):
                if dist < min_supp_dist:
                    min_supp_dist = dist
                    active_support = {
                        "level": s,
                        "label": label,
                        "distance": dist,
                        "bouncing": current_price >= s
                    }

        # Active Resistance Check
        active_resistance = None
        min_res_dist = float('inf')
        for r, label in all_resistances:
            dist = abs(current_price - r)
            if dist < threshold and current_price <= (r + (0.5 * atr)):
                if dist < min_res_dist:
                    min_res_dist = dist
                    active_resistance = {
                        "level": r,
                        "label": label,
                        "distance": dist,
                        "rejecting": current_price <= r
                    }

        return {
            "active_support": active_support,
            "active_resistance": active_resistance,
            "support_levels": all_supports,
            "resistance_levels": all_resistances
        }

    @staticmethod
    def detect_gold_institutional_zones(current_price: float, df_trend: pd.DataFrame, df_entry: pd.DataFrame) -> Dict[str, Any]:
        """
        Specialized Gold (XAUUSD) Institutional Core Analytics:
        1. Psychological Round Number Magnet ($25, $50, $100 levels: 4300, 4325, 4350, 4375, 4400).
        2. Asian Session High/Low Liquidity Pools & Sweeps.
        3. Multi-Timeframe High-Volume Nodes.
        """
        # 1. Psychological Round Number Magnets
        grid_25 = round(current_price / 25.0) * 25.0
        grid_50 = round(current_price / 50.0) * 50.0
        grid_100 = round(current_price / 100.0) * 100.0
        
        dist_to_key_level = abs(current_price - grid_25)
        at_psychological_level = dist_to_key_level <= 3.0  # Within $3 of a $25/$50 round number

        # 2. Asian Session Range & Liquidity Pool Sweeps
        asian_high = None
        asian_low = None
        asian_sweep = None

        if 'time' in df_trend.columns or isinstance(df_trend.index, pd.DatetimeIndex):
            try:
                # Get last 24h of data
                df_last_day = df_trend.tail(24)
                asian_high = df_last_day['high'].max()
                asian_low = df_last_day['low'].min()
                
                # Check for Asian High Sweep (Price wicked above Asian high and pulled back)
                if current_price > asian_high - 2.0 and df_entry['high'].iloc[-1] > asian_high:
                    asian_sweep = "ASIAN_HIGH_SWEEP"
                elif current_price < asian_low + 2.0 and df_entry['low'].iloc[-1] < asian_low:
                    asian_sweep = "ASIAN_LOW_SWEEP"
            except Exception:
                pass

        return {
            "nearest_psychological_25": grid_25,
            "nearest_psychological_50": grid_50,
            "nearest_psychological_100": grid_100,
            "at_psychological_level": at_psychological_level,
            "psychological_dist": dist_to_key_level,
            "asian_high": asian_high,
            "asian_low": asian_low,
            "asian_sweep": asian_sweep
        }

    @staticmethod
    def calculate_adr(df_daily: pd.DataFrame, current_price: float, symbol: str) -> Dict[str, Any]:
        """
        Calculates 14-Day Average Daily Range (ADR) and % ADR Consumed.
        Prevents chasing breakouts when daily range is exhausted (>120%).
        """
        if df_daily is None or len(df_daily) < 5:
            return {"adr_14": 0.0, "today_range": 0.0, "adr_pct_consumed": 0.0, "is_adr_exhausted": False}

        try:
            if len(df_daily) > 1:
                past_ranges = (df_daily['high'].iloc[:-1] - df_daily['low'].iloc[:-1]).tail(14)
                adr_14 = float(past_ranges.mean())
            else:
                adr_14 = float(df_daily['high'].iloc[0] - df_daily['low'].iloc[0])

            today_candle = df_daily.iloc[-1]
            today_range = float(today_candle['high'] - today_candle['low'])

            pct_consumed = (today_range / max(adr_14, 1e-6)) * 100.0
            is_exhausted = pct_consumed >= 120.0

            return {
                "adr_14": adr_14,
                "today_range": today_range,
                "adr_pct_consumed": round(pct_consumed, 1),
                "is_adr_exhausted": is_exhausted
            }
        except Exception:
            return {"adr_14": 0.0, "today_range": 0.0, "adr_pct_consumed": 0.0, "is_adr_exhausted": False}

    @staticmethod
    def detect_volume_absorption(df_entry: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Volume Spread Analysis (VSA) & Institutional Absorption Detector:
        Detects smart money volume absorption (high tick volume with small body or rejection wick).
        """
        if df_entry is None or len(df_entry) < 20 or 'tick_volume' not in df_entry.columns:
            return {"is_absorption": False, "type": "NONE", "volume_ratio": 1.0}

        try:
            vol = df_entry['tick_volume']
            vol_sma = vol.rolling(20).mean().iloc[-1]
            latest_vol = vol.iloc[-1]
            prev_vol = vol.iloc[-2]

            max_recent_vol = max(latest_vol, prev_vol)
            vol_ratio = max_recent_vol / max(vol_sma, 1.0)

            latest_c = df_entry.iloc[-1]
            body = abs(latest_c['close'] - latest_c['open'])
            candle_range = latest_c['high'] - latest_c['low']

            is_absorption = False
            abs_type = "NONE"

            if vol_ratio >= 1.6:
                upper_wick = latest_c['high'] - max(latest_c['close'], latest_c['open'])
                lower_wick = min(latest_c['close'], latest_c['open']) - latest_c['low']

                # Long upper wick with high volume = Bearish Absorption / Rejection
                if upper_wick >= 0.55 * max(candle_range, 1e-6):
                    is_absorption = True
                    abs_type = "BEARISH_ABSORPTION"
                # Long lower wick with high volume = Bullish Absorption / Rejection
                elif lower_wick >= 0.55 * max(candle_range, 1e-6):
                    is_absorption = True
                    abs_type = "BULLISH_ABSORPTION"
                # High Volume + Small Body = Institutional Accumulation / Absorption
                elif body <= 0.45 * max(candle_range, 1e-6):
                    is_absorption = True
                    abs_type = "BULLISH_ABSORPTION" if latest_c['close'] >= latest_c['open'] else "BEARISH_ABSORPTION"

            return {
                "is_absorption": is_absorption,
                "type": abs_type,
                "volume_ratio": round(vol_ratio, 2)
            }
        except Exception:
            return {"is_absorption": False, "type": "NONE", "volume_ratio": 1.0}

    def analyze_symbol(
        self,
        symbol: str,
        df_trend: pd.DataFrame,
        df_entry: pd.DataFrame,
        df_macro: Optional[pd.DataFrame] = None,
        df_trigger: Optional[pd.DataFrame] = None,
        df_daily: Optional[pd.DataFrame] = None,
        ticks: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """Full market analysis combining 4-Tier Multi-Timeframe Fractal, Price Action, Support/Resistance, SMC, ADR, VSA & Weather Radar."""
        df_trend = self.calculate_indicators(df_trend)
        df_entry = self.calculate_indicators(df_entry)

        latest_trend = df_trend.iloc[-1]
        ema_50 = latest_trend['ema_50']
        ema_200 = latest_trend['ema_200']
        close_price = latest_trend['close']

        if close_price > ema_50 > ema_200:
            trend_direction = "BULLISH"
        elif close_price < ema_50 < ema_200:
            trend_direction = "BEARISH"
        else:
            trend_direction = "NEUTRAL"

        # SMC Patterns
        fvgs = self.detect_fvg(df_entry, symbol=symbol)
        order_blocks = self.detect_order_blocks(df_entry)

        # Market Maker Stop Hunts & Liquidity Sweeps
        liquidity_sweep = self.mm_game.detect_liquidity_sweep(df_entry)
        judas_swing = self.mm_game.detect_judas_swing(df_entry, session_name="LONDON")

        # Candlestick & Structure Chart Patterns
        c_patterns = self.chart_patterns.detect_candlestick_patterns(df_entry)
        s_pattern = self.chart_patterns.detect_double_top_bottom(df_entry)

        # Market Weather Predictive Radar Scan
        weather_forecast = self.weather_engine.forecast_market_weather(df_trend, df_entry, symbol=symbol)

        recent_fvgs = [f for f in fvgs if f['index'] >= len(df_entry) - 15]
        bullish_fvg = next((f for f in reversed(recent_fvgs) if f['type'] == "BULLISH_FVG"), None)
        bearish_fvg = next((f for f in reversed(recent_fvgs) if f['type'] == "BEARISH_FVG"), None)

        recent_obs = order_blocks[-5:] if order_blocks else []
        bullish_ob = next((ob for ob in reversed(recent_obs) if ob['type'] == "BULLISH_OB"), None)
        bearish_ob = next((ob for ob in reversed(recent_obs) if ob['type'] == "BEARISH_OB"), None)

        latest_entry = df_entry.iloc[-1]
        atr_val = latest_entry['atr'] if not np.isnan(latest_entry['atr']) else 0.0010
        rsi_val = latest_entry['rsi'] if not np.isnan(latest_entry['rsi']) else 50.0

        # Detect Key Support and Resistance Zones (combines H1 + M15 pivots)
        sr_data = self.detect_key_support_resistance(
            df_trend=df_trend,
            df_entry=df_entry,
            current_price=latest_entry['close'],
            atr=atr_val,
            symbol=symbol
        )

        # Specialized Gold Institutional Analysis
        gold_intel = None
        if symbol == "XAUUSD":
            gold_intel = self.detect_gold_institutional_zones(
                current_price=latest_entry['close'],
                df_trend=df_trend,
                df_entry=df_entry
            )

        # Average Daily Range (ADR)
        adr_intel = self.calculate_adr(df_daily, current_price=latest_entry['close'], symbol=symbol)

        # Volume Spread Analysis (VSA)
        vsa_intel = self.detect_volume_absorption(df_entry, symbol=symbol)

        # Aladdin Order Flow Quant (Premium/Discount, OTE 70.5%, Inducement, Killzones)
        premium_discount = self.order_flow_quant.evaluate_premium_discount(df_trend, latest_entry['close'])
        ote_buy = self.order_flow_quant.compute_ote_fibonacci_array(df_entry, latest_entry['close'], "BUY")
        ote_sell = self.order_flow_quant.compute_ote_fibonacci_array(df_entry, latest_entry['close'], "SELL")
        inducement = self.order_flow_quant.detect_eqh_eql_inducement(df_entry, symbol=symbol)
        candle_time = latest_entry['time'] if 'time' in latest_entry else None
        killzone = self.order_flow_quant.get_active_killzone(candle_time)

        # Quantitative Statistical Regime Classification
        regime_intel = self.regime_detector.detect_regime(df_trend)

        # Microsoft Qlib Alpha158 Quantitative Momentum & VWAP Factors
        qlib_intel = self.qlib_engine.compute_alpha_factors(df_trend)

        # Global Inter-Market Macro Correlation Radar (DXY, US10Y Yields, Gold Tailwinds)
        intermarket_intel = self.intermarket_radar.fetch_intermarket_metrics()

        # Economic Calendar High-Impact News Blackout Radar
        news_clearance = self.calendar_radar.evaluate_news_clearance(symbol)

        # Institutional Insider Whales & Dark Pool Liquidity Anomaly Detector
        dark_pool_intel = self.insider_whales.detect_dark_pool_anomalies(df_entry)
        political_shock = self.insider_whales.evaluate_political_macro_shock()

        # 50-Year Market Crisis & History Analogue Engine
        historical_analogue = self.history_encyclopedia.match_nearest_historical_analogue(
            current_volatility_z=float(regime_intel.get("volatility_zscore", 1.5)),
            dxy_momentum=-0.5 if intermarket_intel.get("dxy_trend") == "BEARISH" else 0.5
        )

        # Cross-Asset Contagion, GSR Ratio & Commodity Matrix Engine
        cross_asset_matrix = self.cross_market.evaluate_cross_asset_macro_matrix()

        # Lee-Ready Cumulative Volume Delta (CVD) Order Flow
        of_data = self.order_flow_quant.compute_tick_cvd(ticks)

        # Multi-Timeframe (M15 + H1 + H4) Trend Confluence Engine
        mtf_confluence = None
        mtf_confluence_ok = True
        mtf_confluence_direction = None
        if df_macro is not None and len(df_macro) >= 20:
            mtf_confluence_ok, mtf_confluence_direction, mtf_confluence = self.confluence_filter.evaluate_trend_confluence(
                m15_df=df_entry,
                h1_df=df_trend,
                h4_df=df_macro,
                symbol=symbol,
            )

        return {
            "symbol": symbol,
            "current_price": latest_entry['close'],
            "trend_direction": trend_direction,
            "mtf_confluence": mtf_confluence,
            "mtf_confluence_ok": mtf_confluence_ok,
            "mtf_confluence_direction": mtf_confluence_direction,
            "rsi": rsi_val,
            "atr": atr_val,
            "bullish_fvg": bullish_fvg,
            "bearish_fvg": bearish_fvg,
            "bullish_ob": bullish_ob,
            "bearish_ob": bearish_ob,
            "active_support": sr_data["active_support"],
            "active_resistance": sr_data["active_resistance"],
            "support_levels": sr_data["support_levels"],
            "resistance_levels": sr_data["resistance_levels"],
            "liquidity_sweep": liquidity_sweep,
            "judas_swing": judas_swing,
            "candlestick_patterns": c_patterns.get("patterns", []),
            "structure_pattern": s_pattern.get("structure_pattern"),
            "weather_forecast": weather_forecast,
            "fincept_sentiment": latest_entry.get("fincept_sentiment", 50.0),
            "gold_intel": gold_intel,
            "adr_intel": adr_intel,
            "vsa_intel": vsa_intel,
            "premium_discount": premium_discount,
            "ote_buy": ote_buy,
            "ote_sell": ote_sell,
            "inducement": inducement,
            "killzone": killzone,
            "regime_intel": regime_intel,
            "qlib_intel": qlib_intel,
            "intermarket_intel": intermarket_intel,
            "news_clearance": news_clearance,
            "dark_pool_intel": dark_pool_intel,
            "political_shock": political_shock,
            "historical_analogue": historical_analogue,
            "cross_asset_matrix": cross_asset_matrix,
            "order_flow": of_data,
            "candle_time": candle_time,
            "df_entry": df_entry
        }
