"""
broker_bbook_defense_shield.py — Broker B-Book Anti-Manipulation & Rollover Defense Shield.
Monitors broker execution latency (execution ping in ms), spreads during midnight rollover
(21:00-22:00 UTC), and switches execution dynamically from Market Orders to positive-slippage
Limit-Only mode during toxic broker liquidity voids.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("BrokerBBookDefense")


class BrokerBBookDefenseShield:
    """
    Advanced Broker Manipulation & Toxic Rollover Armor.
    """

    MAX_SAFE_SPREAD_PIPS = {
        "XAUUSD": 35.0,  # 3.5 pips / $0.35 on Gold
        "XAGUSD": 6.0,
        "EURUSD": 2.0,
        "GBPUSD": 2.5,
        "USDJPY": 2.2,
        "BTCUSD": 50.0
    }

    MAX_EXECUTION_LATENCY_MS = 250.0  # Max acceptable broker ping

    def __init__(self):
        self.latency_history: List[float] = []
        self.spread_violations_count = 0
        logger.info("[BrokerBBookDefenseShield] Armed with Toxic Rollover & B-Book latency guards.")

    def is_rollover_window(self, current_utc_time: Optional[datetime] = None) -> bool:
        """
        Detects if current time falls within the daily New York close / Asian open rollover window (21:00 - 22:15 UTC).
        """
        now = current_utc_time or datetime.now(timezone.utc)
        hour = now.hour
        minute = now.minute
        # 21:00 to 22:15 UTC is the standard interbank rollover void
        if hour == 21:
            return True
        if hour == 22 and minute <= 15:
            return True
        return False

    def evaluate_spread_safety(self, symbol: str, current_spread_pips: float) -> Dict[str, Any]:
        """
        Audits current spread against historical normal bounds.
        """
        clean_sym = symbol.replace("m", "").replace("c", "").upper()
        max_safe = self.MAX_SAFE_SPREAD_PIPS.get(clean_sym, 5.0)

        is_safe = (current_spread_pips <= max_safe)
        if not is_safe:
            self.spread_violations_count += 1
            logger.warning(
                f"[B-Book Shield Warning] Toxic spread detected on {symbol}: "
                f"{current_spread_pips:.1f} pips (Safe Ceiling: {max_safe:.1f} pips)."
            )

        return {
            "symbol": symbol,
            "current_spread_pips": current_spread_pips,
            "max_safe_spread_pips": max_safe,
            "is_safe": is_safe,
            "action": "ALLOW_EXECUTION" if is_safe else "BLOCK_MARKET_ORDER_USE_LIMIT_ONLY"
        }

    def measure_execution_latency(self, ping_ms: float) -> Dict[str, Any]:
        """
        Tracks broker round-trip execution latency and flags delay manipulation.
        """
        self.latency_history.append(ping_ms)
        if len(self.latency_history) > 100:
            self.latency_history.pop(0)

        avg_latency = sum(self.latency_history) / len(self.latency_history)
        is_latency_safe = (ping_ms <= self.MAX_EXECUTION_LATENCY_MS)

        return {
            "last_latency_ms": ping_ms,
            "avg_latency_ms": round(avg_latency, 2),
            "is_latency_safe": is_latency_safe,
            "execution_channel": "INSTANT_DIRECT" if is_latency_safe else "POSITIVE_SLIPPAGE_LIMIT_SHIELD"
        }

    def audit_trade_safety(self, symbol: str, spread_pips: float, ping_ms: float = 45.0) -> Dict[str, Any]:
        """
        Comprehensive pre-execution safety audit.
        """
        in_rollover = self.is_rollover_window()
        spread_audit = self.evaluate_spread_safety(symbol, spread_pips)
        latency_audit = self.measure_execution_latency(ping_ms)

        passed = (not in_rollover) and spread_audit["is_safe"] and latency_audit["is_latency_safe"]

        recommended_order_type = "MARKET"
        if in_rollover or not spread_audit["is_safe"]:
            recommended_order_type = "LIMIT_BRACKET_ONLY"

        return {
            "safe_to_execute": passed,
            "in_rollover_window": in_rollover,
            "spread_audit": spread_audit,
            "latency_audit": latency_audit,
            "recommended_order_type": recommended_order_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
