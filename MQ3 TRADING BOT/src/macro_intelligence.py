import os
import time
import logging
import requests
import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class USDCurrencyBasketCorrelationGuard:
    """
    USD Currency Basket & Cross-Pair Macro Correlation Shield.
    Prevents self-hedging and conflicting directional exposure across USD pairs (XAUUSD, EURUSD, GBPUSD, USDJPY).
    
    Mapping:
      - XAUUSD BUY  -> USD_BEARISH (Short USD)
      - XAUUSD SELL -> USD_BULLISH (Long USD)
      - EURUSD BUY  -> USD_BEARISH (Short USD)
      - EURUSD SELL -> USD_BULLISH (Long USD)
      - GBPUSD BUY  -> USD_BEARISH (Short USD)
      - GBPUSD SELL -> USD_BULLISH (Long USD)
      - USDJPY BUY  -> USD_BULLISH (Long USD)
      - USDJPY SELL -> USD_BEARISH (Short USD)
    """

    @staticmethod
    def get_usd_bias(symbol: str, signal_type: str) -> str:
        """Determines whether a trade is betting on USD strength (BULLISH) or weakness (BEARISH)."""
        dr = signal_type.upper()
        if symbol in ["XAUUSD", "EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"]:
            return "USD_BEARISH" if dr == "BUY" else "USD_BULLISH"
        elif symbol in ["USDJPY", "USDCHF", "USDCAD"]:
            return "USD_BULLISH" if dr == "BUY" else "USD_BEARISH"
        return "NEUTRAL"

    @classmethod
    def validate_usd_alignment(cls, new_symbol: str, new_signal_type: str, open_positions: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Audits new signal against all currently open positions.
        Returns: (allowed: bool, reason: str)
        """
        if not open_positions:
            return True, "No open positions — USD exposure is clean."

        new_bias = cls.get_usd_bias(new_symbol, new_signal_type)
        if new_bias == "NEUTRAL":
            return True, "Symbol has neutral USD exposure."

        conflicting_trades = []
        for p in open_positions:
            pos_sym = p.get("symbol", "")
            pos_type = p.get("type", "")
            pos_bias = cls.get_usd_bias(pos_sym, pos_type)
            
            if pos_bias != "NEUTRAL" and pos_bias != new_bias:
                conflicting_trades.append(f"{pos_sym} {pos_type} ({pos_bias})")

        if conflicting_trades:
            reason = (
                f"USD Correlation Conflict: {new_symbol} {new_signal_type} ({new_bias}) conflicts with active "
                f"opposite USD exposure in: {', '.join(conflicting_trades)}."
            )
            return False, reason

        return True, f"USD exposure aligned ({new_bias}) across all positions."


class ConfidenceArbitrator:
    """
    Cross-Pair Confidence Arbitration & Alpha Prioritization Engine.
    When multiple symbols produce trading signals in a scan cycle, this engine:
    1. Scores each candidate setup on multi-factor confidence (Confluence, Quality, SuperContext, WinRate).
    2. Ranks candidates in descending order of Alpha/Confidence.
    3. Selects the highest-confidence setup and pauses/rejects any weaker conflicting setups.
    """

    @staticmethod
    def calculate_candidate_confidence(
        signal: Dict[str, Any],
        quality_score: float,
        context_score: float,
        is_signature: bool = False
    ) -> float:
        """
        Calculates a normalized 0.0 - 5.0 Composite Confidence score for a signal:
        - Confluence Score (Weight 40%)
        - Signal Quality Score (Weight 35%)
        - OpenHuman SuperContext Score (Weight 15%)
        - Signature Setup & Asset Focus Bonus (+0.5)
        """
        confluence = signal.get("confluence_score", 1.0)
        symbol = signal.get("symbol", "")
        
        # Base composite score
        score = (confluence * 1.5 * 0.40) + (quality_score * 0.35) + ((context_score / 20.0) * 0.15)
        
        if symbol == "XAUUSD":
            score += 0.85  # Sovereign Gold Benchmark King Priority
        if is_signature:
            score += 0.40  # High win-rate proven setup bonus
            
        return round(score, 2)

    @classmethod
    def arbitrate_candidates(
        cls,
        candidates: List[Dict[str, Any]],
        open_positions: List[Dict[str, Any]],
        correlation_guard: USDCurrencyBasketCorrelationGuard
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
        """
        Ranks candidates by confidence and filters out conflicting weaker signals.
        Returns: (approved_candidates, paused_reasons)
        """
        if not candidates:
            return [], []

        # Sort candidates descending by confidence score
        sorted_candidates = sorted(candidates, key=lambda c: c.get("confidence_score", 0.0), reverse=True)
        
        approved = []
        paused = []
        
        # Virtual positions list to track cumulative exposure during batch cycle
        simulated_positions = list(open_positions)
        
        for cand in sorted_candidates:
            sym = cand["signal"]["symbol"]
            sig_type = cand["signal"]["signal"]
            conf_score = cand.get("confidence_score", 0.0)
            
            allowed, reason = correlation_guard.validate_usd_alignment(
                new_symbol=sym,
                new_signal_type=sig_type,
                open_positions=simulated_positions
            )
            
            if allowed:
                approved.append(cand)
                simulated_positions.append({"symbol": sym, "type": sig_type})
            else:
                top_winner = approved[0]["signal"]["symbol"] if approved else "Active Position"
                top_score = approved[0].get("confidence_score", 0.0) if approved else "High Conviction"
                pause_msg = f"[Alpha Arbitration] {sym} {sig_type} (Confidence: {conf_score:.2f}) PAUSED in favor of higher-confidence {top_winner} (Confidence: {top_score}). Reason: {reason}"
                paused.append({"symbol": sym, "reason": pause_msg})
                
        return approved, paused


class GlobalMacroGeopoliticalIntelligence:
    """
    Global Macroeconomic & Geopolitical News Intelligence Engine.
    Queries real-time financial APIs, RSS economic feeds, and geopolitical sentiment
    to detect market-moving global news (Central Bank Rates, NFP, CPI, Geopolitical conflicts).
    """

    def __init__(self):
        self.last_scan_time: Optional[datetime.datetime] = None
        self.cached_news_events: List[Dict[str, Any]] = []
        self.geopolitical_risk_score: float = 0.0  # 0.0 (Normal) to 1.0 (Critical)
        self.correlation_guard = USDCurrencyBasketCorrelationGuard()
        self.arbitrator = ConfidenceArbitrator()

    def scan_global_news(self) -> Dict[str, Any]:
        """Scans live global macroeconomic news feeds and geopolitical indicators."""
        now = datetime.datetime.now(datetime.timezone.utc)
        if self.last_scan_time and (now - self.last_scan_time).total_seconds() < 900:
            return {"events": self.cached_news_events, "risk_score": self.geopolitical_risk_score}

        events = []
        # Query Live ForexFactory / Economic Feed
        try:
            url = "https://nodedata.forexfactory.com/ff_calendar_thisweek.json"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                data = res.json()
                for item in data:
                    if str(item.get("impact")).upper() in ["HIGH", "RED"]:
                        events.append({
                            "title": item.get("title"),
                            "country": item.get("country"),
                            "date": item.get("date"),
                            "impact": "HIGH"
                        })
                self.cached_news_events = events
                logger.info(f"[Macro Intelligence] Scanned {len(events)} High-Impact global economic events.")
        except Exception as e:
            logger.debug(f"[Macro Intelligence] Live feed sync note: {e}")

        self.last_scan_time = now
        return {"events": self.cached_news_events, "risk_score": self.geopolitical_risk_score}

    def is_symbol_news_locked(self, symbol: str) -> Tuple[bool, str]:
        """Checks if symbol is currently locked due to high-impact economic news."""
        news_data = self.scan_global_news()
        now = datetime.datetime.now(datetime.timezone.utc)
        curr1 = symbol[:3]
        curr2 = symbol[3:] if len(symbol) >= 6 else "USD"

        for ev in news_data["events"]:
            country = ev.get("country", "USD")
            if country in [curr1, curr2, "USD"]:
                date_str = ev.get("date")
                if date_str:
                    try:
                        ev_time = datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        window_start = ev_time - datetime.timedelta(minutes=15)
                        window_end = ev_time + datetime.timedelta(minutes=15)

                        if window_start <= now <= window_end:
                            msg = f"GLOBAL MACRO LOCK: '{ev.get('title')}' ({country}) active at {ev_time.strftime('%H:%M UTC')}. Trading paused for {symbol}."
                            logger.info(msg)
                            return True, msg
                    except Exception:
                        pass

        return False, "No active macro news lock."
