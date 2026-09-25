"""
macro_surveillance.py — Institutional Macro Surveillance Engine for J.A.R.V.I.S.
Provides:
  1. 28-Pair Currency Strength Meter (CSM) for USD, EUR, GBP, JPY, AUD, CAD, CHF, NZD.
  2. Central Bank Interest Rate Differential Matrix (Fed, ECB, BoE, BoJ) with policy bias.
  3. Economic Calendar News Blackout Buffer (Deterministic 15-minute Pre/Post High Impact).
"""

import math
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("MacroSurveillance")

# The 8 Major Global Currencies
MAJOR_CURRENCIES = ["USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"]

# All 28 Canonical Currency Pairs
PAIRS_28 = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
    "EURGBP", "EURJPY", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
    "GBPJPY", "GBPCHF", "GBPAUD", "GBPCAD", "GBPNZD",
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
    "CADJPY", "CADCHF",
    "CHFJPY",
    "NZDJPY", "NZDCAD", "NZDCHF"
]


class CurrencyStrengthMeter:
    """
    Quantitative Currency Strength Meter (CSM).
    Calculates normalized relative currency strength scores (0.0 to 10.0) across 28 cross pairs.
    """

    def __init__(self):
        # Baseline reference price points for synthetic / live simulation
        self._reference_rates: Dict[str, float] = {
            "EURUSD": 1.0850, "GBPUSD": 1.3020, "USDJPY": 152.40,
            "USDCHF": 0.8650, "USDCAD": 1.3850, "AUDUSD": 0.6580, "NZDUSD": 0.5980,
            "EURGBP": 0.8333, "EURJPY": 165.35, "EURCHF": 0.9385, "EURAUD": 1.6490, "EURCAD": 1.5025, "EURNZD": 1.8140,
            "GBPJPY": 198.40, "GBPCHF": 1.1260, "GBPAUD": 1.9785, "GBPCAD": 1.8030, "GBPNZD": 2.1770,
            "AUDJPY": 100.28, "AUDCAD": 0.9110, "AUDCHF": 0.5690, "AUDNZD": 1.1000,
            "CADJPY": 110.05, "CADCHF": 0.6245,
            "CHFJPY": 176.15,
            "NZDJPY": 91.15, "NZDCAD": 0.8280, "NZDCHF": 0.5170
        }
        # Dynamic rate storage
        self._rates = dict(self._reference_rates)
        self._last_update_ts = time.time()

    def update_rate(self, pair: str, price: float):
        """Updates a specific pair rate."""
        p_clean = pair.replace("/", "").replace("_", "").upper()
        if p_clean in PAIRS_28:
            self._rates[p_clean] = float(price)
            self._last_update_ts = time.time()

    def update_bulk_rates(self, quotes: Dict[str, float]):
        """Updates multiple pair rates."""
        for p, price in quotes.items():
            self.update_rate(p, price)

    def calculate_strength(self, pair_changes: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Calculates currency strength scores across 8 currencies.
        
        Args:
            pair_changes: Optional mapping of pair to percentage change (e.g. {"EURUSD": 0.25}).
                         If None, calculates relative delta from baseline reference rates.
                         
        Returns:
            Dict containing currency scores (0.0 to 10.0), rankings, pair biases, and strongest/weakest.
        """
        # Raw accumulation buckets for each currency
        scores_raw: Dict[str, float] = {c: 0.0 for c in MAJOR_CURRENCIES}
        pair_data: Dict[str, float] = {}

        if pair_changes is not None:
            for p in PAIRS_28:
                pct = pair_changes.get(p, pair_changes.get(f"{p[:3]}/{p[3:]}", 0.0))
                pair_data[p] = pct
        else:
            # Calculate from current rates vs reference rates
            for p, cur_rate in self._rates.items():
                ref_rate = self._reference_rates.get(p, cur_rate)
                pct = ((cur_rate - ref_rate) / ref_rate) * 100.0 if ref_rate > 0 else 0.0
                pair_data[p] = pct

        # Accumulate score based on each pair's movement
        for p, pct in pair_data.items():
            base = p[:3]
            quote = p[3:]
            if base in scores_raw and quote in scores_raw:
                scores_raw[base] += pct
                scores_raw[quote] -= pct

        # Normalize raw scores to 0.0 - 10.0 range
        # Average number of pairs per currency is 7.
        # Theoretical max movement +- 3.5% across pairs -> +-25 raw points
        raw_vals = list(scores_raw.values())
        min_v = min(raw_vals) if raw_vals else 0.0
        max_v = max(raw_vals) if raw_vals else 0.0
        spread = max_v - min_v

        normalized_scores: Dict[str, float] = {}
        for c in MAJOR_CURRENCIES:
            if spread > 0.001:
                norm = ((scores_raw[c] - min_v) / spread) * 10.0
            else:
                # Neutral baseline with slight natural variation if zero spread
                norm = 5.0 + (scores_raw[c] * 0.5)
            normalized_scores[c] = round(max(0.0, min(10.0, norm)), 2)

        # Ranked list of currencies
        ranked = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)
        strongest = ranked[0]
        weakest = ranked[-1]

        # Calculate high-conviction pair biases
        pair_biases = []
        for p in PAIRS_28:
            base = p[:3]
            quote = p[3:]
            diff = normalized_scores[base] - normalized_scores[quote]
            if abs(diff) >= 2.0:
                direction = "LONG" if diff > 0 else "SHORT"
                strength = "HIGH" if abs(diff) >= 4.0 else "MEDIUM"
                pair_biases.append({
                    "pair": f"{base}/{quote}",
                    "bias": direction,
                    "delta": round(diff, 2),
                    "conviction": strength
                })

        # Sort pair biases by absolute delta
        pair_biases.sort(key=lambda x: abs(x["delta"]), reverse=True)

        return {
            "currency_strength": normalized_scores,
            "rankings": [{"rank": i + 1, "currency": c, "score": s} for i, (c, s) in enumerate(ranked)],
            "strongest": {"currency": strongest[0], "score": strongest[1]},
            "weakest": {"currency": weakest[0], "score": weakest[1]},
            "top_pair_biases": pair_biases[:6],
            "pairs_evaluated": len(pair_data),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class CentralBankRateMatrix:
    """
    Central Bank Policy & Interest Rate Differential Matrix.
    Tracks benchmark interest rates for Fed, ECB, BoE, BoJ and calculates pair yield spreads.
    """

    def __init__(self):
        # Benchmark institutional policy rates (%) and stance
        self.banks: Dict[str, Dict[str, Any]] = {
            "FED": {
                "name": "Federal Reserve (US)",
                "currency": "USD",
                "rate": 5.50,
                "range": "5.25% - 5.50%",
                "bias": "HAWKISH_HOLD",
                "next_meeting": "2026-11-05",
                "last_action": "Pause at 5.50%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 2.9
            },
            "ECB": {
                "name": "European Central Bank",
                "currency": "EUR",
                "rate": 3.75,
                "range": "3.75%",
                "bias": "DOVISH_CUTTING",
                "next_meeting": "2026-10-23",
                "last_action": "Cut -25 bps to 3.75%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 2.2
            },
            "BOE": {
                "name": "Bank of England",
                "currency": "GBP",
                "rate": 5.00,
                "range": "5.00%",
                "bias": "MODERATE_NEUTRAL",
                "next_meeting": "2026-11-06",
                "last_action": "Cut -25 bps to 5.00%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 2.3
            },
            "BOJ": {
                "name": "Bank of Japan",
                "currency": "JPY",
                "rate": 0.25,
                "range": "0.25%",
                "bias": "HAWKISH_NORMALIZING",
                "next_meeting": "2026-10-30",
                "last_action": "Hike +15 bps to 0.25%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 2.8
            },
            # Additional major central banks
            "RBA": {
                "name": "Reserve Bank of Australia",
                "currency": "AUD",
                "rate": 4.35,
                "range": "4.35%",
                "bias": "HAWKISH_HOLD",
                "next_meeting": "2026-11-05",
                "last_action": "Hold at 4.35%",
                "inflation_target_pct": 2.5,
                "current_cpi_pct": 3.8
            },
            "BOC": {
                "name": "Bank of Canada",
                "currency": "CAD",
                "rate": 4.25,
                "range": "4.25%",
                "bias": "DOVISH_CUTTING",
                "next_meeting": "2026-10-23",
                "last_action": "Cut -25 bps to 4.25%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 2.5
            },
            "SNB": {
                "name": "Swiss National Bank",
                "currency": "CHF",
                "rate": 1.25,
                "range": "1.25%",
                "bias": "DOVISH_CUTTING",
                "next_meeting": "2026-12-12",
                "last_action": "Cut -25 bps to 1.25%",
                "inflation_target_pct": 1.5,
                "current_cpi_pct": 1.1
            },
            "RBNZ": {
                "name": "Reserve Bank of New Zealand",
                "currency": "NZD",
                "rate": 5.25,
                "range": "5.25%",
                "bias": "MODERATE_HOLD",
                "next_meeting": "2026-11-27",
                "last_action": "Hold at 5.25%",
                "inflation_target_pct": 2.0,
                "current_cpi_pct": 3.3
            }
        }

    def compute_matrix(self) -> Dict[str, Any]:
        """
        Computes the full rate differential matrix for core banks and all major currency pairs.
        """
        core_banks = ["FED", "ECB", "BOE", "BOJ"]
        diff_matrix: Dict[str, float] = {}

        # Pairwise central bank differentials
        for b1 in core_banks:
            for b2 in core_banks:
                if b1 != b2:
                    diff = self.banks[b1]["rate"] - self.banks[b2]["rate"]
                    diff_matrix[f"{b1}_{b2}"] = round(diff, 2)

        # Cross-pair yield differentials & carry trade bias
        pair_carry: Dict[str, Dict[str, Any]] = {}
        for b1 in core_banks:
            c1 = self.banks[b1]["currency"]
            for b2 in core_banks:
                c2 = self.banks[b2]["currency"]
                if c1 != c2:
                    pair_key = f"{c1}/{c2}"
                    spread = self.banks[b1]["rate"] - self.banks[b2]["rate"]
                    
                    if spread >= 2.0:
                        bias = "STRONG_CARRY_LONG"
                    elif spread >= 0.5:
                        bias = "MILD_CARRY_LONG"
                    elif spread <= -2.0:
                        bias = "STRONG_CARRY_SHORT"
                    elif spread <= -0.5:
                        bias = "MILD_CARRY_SHORT"
                    else:
                        bias = "NEUTRAL_YIELD_PARITY"

                    pair_carry[pair_key] = {
                        "base_rate": self.banks[b1]["rate"],
                        "quote_rate": self.banks[b2]["rate"],
                        "spread_pct": round(spread, 2),
                        "carry_bias": bias
                    }

        return {
            "policy_rates": {k: v["rate"] for k, v in self.banks.items()},
            "bank_details": self.banks,
            "rate_differentials": diff_matrix,
            "pair_carry_matrix": pair_carry,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class EconomicNewsBlackoutManager:
    """
    Economic Calendar News Impact & Circuit Breaker Manager.
    Calculates deterministic 15-minute Pre-News and Post-News trading blackout buffer.
    """

    def __init__(self, blackout_minutes_before: int = 15, blackout_minutes_after: int = 15, include_reference_events: bool = True):
        self.blackout_before = blackout_minutes_before
        self.blackout_after = blackout_minutes_after
        self.include_reference_events = include_reference_events
        self.manual_events: List[Dict[str, Any]] = []

    def inject_event(
        self,
        title: str,
        currency: str,
        event_time_utc: datetime,
        impact: str = "HIGH"
    ) -> Dict[str, Any]:
        """Injects an event for testing or deterministic blackout verification."""
        if event_time_utc.tzinfo is None:
            event_time_utc = event_time_utc.replace(tzinfo=timezone.utc)
        ev = {
            "title": title,
            "currency": currency.upper(),
            "impact": impact.upper(),
            "event_time_utc": event_time_utc,
            "time_iso": event_time_utc.isoformat(),
            "is_high_impact": impact.upper() in ["HIGH", "RED", "CRITICAL"]
        }
        self.manual_events.append(ev)
        return ev

    def clear_injected_events(self):
        """Clears all manually injected events."""
        self.manual_events = []

    def get_upcoming_schedule(self, now: Optional[datetime] = None, include_defaults: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Returns institutional high-impact macroeconomic calendar events."""
        now_utc = now or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        use_defaults = self.include_reference_events if include_defaults is None else include_defaults
        all_events: List[Dict[str, Any]] = []

        if use_defaults:
            # Baseline recurring high-impact calendar catalysts (placed relative to current day)
            base_date = now_utc.date()
            reference_events = [
                {"title": "US CPI (YoY / MoM)", "currency": "USD", "impact": "HIGH", "hour": 12, "minute": 30},
                {"title": "US Non-Farm Payrolls (NFP)", "currency": "USD", "impact": "HIGH", "hour": 12, "minute": 30},
                {"title": "FOMC Interest Rate Decision", "currency": "USD", "impact": "HIGH", "hour": 18, "minute": 0},
                {"title": "ECB Monetary Policy Statement & Press Conference", "currency": "EUR", "impact": "HIGH", "hour": 12, "minute": 15},
                {"title": "BOE Official Bank Rate Decision", "currency": "GBP", "impact": "HIGH", "hour": 11, "minute": 0},
                {"title": "BOJ Monetary Policy Statement & Press Conference", "currency": "JPY", "impact": "HIGH", "hour": 3, "minute": 30},
                {"title": "US Core PCE Price Index", "currency": "USD", "impact": "HIGH", "hour": 12, "minute": 30}
            ]

            # Add reference events spread across today and tomorrow
            for offset_days in [0, 1]:
                d = base_date + timedelta(days=offset_days)
                for ref in reference_events:
                    ev_time = datetime(d.year, d.month, d.day, ref["hour"], ref["minute"], tzinfo=timezone.utc)
                    all_events.append({
                        "title": ref["title"],
                        "currency": ref["currency"],
                        "impact": ref["impact"],
                        "event_time_utc": ev_time,
                        "time_iso": ev_time.isoformat(),
                        "is_high_impact": True
                    })

        # Add manual events
        all_events.extend(self.manual_events)
        all_events.sort(key=lambda x: x["event_time_utc"])
        return all_events

    def evaluate_blackout_status(
        self,
        symbol: str = "ALL",
        now: Optional[datetime] = None,
        include_defaults: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Evaluates 15-minute Pre/Post High Impact news blackout buffer.
        """
        now_utc = now or datetime.now(timezone.utc)
        if now_utc.tzinfo is None:
            now_utc = now_utc.replace(tzinfo=timezone.utc)

        events = self.get_upcoming_schedule(now_utc, include_defaults=include_defaults)
        sym_clean = symbol.upper().replace("/", "").replace("_", "")

        active_blackout = False
        blackout_reason = None
        active_event_dict = None
        minutes_remaining = None
        upcoming_in_24h = []

        for ev in events:
            ev_time = ev["event_time_utc"]
            delta_sec = (ev_time - now_utc).total_seconds()
            delta_min = delta_sec / 60.0

            # Match symbol currency if not ALL
            ev_curr = ev["currency"]
            relevant = (sym_clean == "ALL") or (ev_curr in sym_clean) or ("USD" in sym_clean and ev_curr == "USD")

            if not relevant:
                continue

            # Upcoming within 24h
            if 0 < delta_min <= 1440:
                upcoming_in_24h.append({
                    "title": ev["title"],
                    "currency": ev_curr,
                    "impact": ev["impact"],
                    "event_time_utc": ev_time.isoformat(),
                    "minutes_until": round(delta_min, 1)
                })

            # Check 15-min circuit breaker: [-15 min, +15 min]
            if -self.blackout_after <= delta_min <= self.blackout_before:
                active_blackout = True
                window_start = ev_time - timedelta(minutes=self.blackout_before)
                window_end = ev_time + timedelta(minutes=self.blackout_after)

                if delta_min >= 0:
                    blackout_reason = f"PRE_NEWS_BLACKOUT: {ev['title']} ({ev_curr}) in {delta_min:.1f}m."
                    minutes_remaining = round(delta_min + self.blackout_after, 1)
                else:
                    since_min = abs(delta_min)
                    blackout_reason = f"POST_NEWS_BLACKOUT: {ev['title']} ({ev_curr}) released {since_min:.1f}m ago. Cooloff active."
                    minutes_remaining = round(self.blackout_after - since_min, 1)

                active_event_dict = {
                    "title": ev["title"],
                    "currency": ev_curr,
                    "impact": ev["impact"],
                    "event_time_utc": ev_time.isoformat(),
                    "minutes_to_event": round(delta_min, 1),
                    "minutes_remaining_in_blackout": minutes_remaining,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat()
                }
                break

        return {
            "blackout_active": active_blackout,
            "blackout_buffer_minutes": {
                "pre_event": self.blackout_before,
                "post_event": self.blackout_after
            },
            "blackout_reason": blackout_reason,
            "minutes_remaining": minutes_remaining,
            "active_event": active_event_dict,
            "upcoming_events": upcoming_in_24h[:10],
            "timestamp": now_utc.isoformat()
        }


class MacroSurveillanceEngine:
    """
    Consolidated Institutional Macro Surveillance Hub.
    Combines CSM, Central Bank Rate Differentials, and 15-minute Blackout Buffer.
    """

    def __init__(self):
        self.csm = CurrencyStrengthMeter()
        self.rate_matrix = CentralBankRateMatrix()
        self.blackout_mgr = EconomicNewsBlackoutManager()

    def get_macro_surveillance_report(self, symbol: str = "ALL") -> Dict[str, Any]:
        """
        Builds the consolidated `/api/research/forex/macro` response.
        Matches Interface Contract exactly.
        """
        csm_data = self.csm.calculate_strength()
        rates_data = self.rate_matrix.compute_matrix()
        blackout_data = self.blackout_mgr.evaluate_blackout_status(symbol=symbol)

        return {
            "ok": True,
            "status": "OPERATIONAL",
            "currency_strength": csm_data["currency_strength"],
            "rankings": csm_data["rankings"],
            "strongest": csm_data["strongest"],
            "weakest": csm_data["weakest"],
            "top_pair_biases": csm_data["top_pair_biases"],
            "rate_differentials": rates_data["rate_differentials"],
            "policy_rates": rates_data["policy_rates"],
            "bank_details": rates_data["bank_details"],
            "pair_carry_matrix": rates_data["pair_carry_matrix"],
            "blackout_active": blackout_data["blackout_active"],
            "blackout_reason": blackout_data["blackout_reason"],
            "minutes_remaining": blackout_data["minutes_remaining"],
            "active_event": blackout_data["active_event"],
            "upcoming_events": blackout_data["upcoming_events"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
_macro_surveillance_engine: Optional[MacroSurveillanceEngine] = None

def get_macro_surveillance_engine() -> MacroSurveillanceEngine:
    global _macro_surveillance_engine
    if _macro_surveillance_engine is None:
        _macro_surveillance_engine = MacroSurveillanceEngine()
    return _macro_surveillance_engine
