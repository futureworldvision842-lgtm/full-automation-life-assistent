import datetime
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class InstitutionalKnowledge:
    """
    Rules & Principles from Institutional Trading Literature & Books
    (ICT / SMC, Wyckoff Market Cycles, Volatility Expansion, Kill Zones).
    """

    @staticmethod
    def get_trading_session(utc_time: datetime.datetime) -> str:
        """Determines active institutional trading session in UTC."""
        hour = utc_time.hour
        if 7 <= hour < 12:
            return "LONDON"
        elif 12 <= hour < 17:
            return "NEW_YORK"
        elif 0 <= hour < 7:
            return "ASIAN"
        else:
            return "OFF_HOURS"

    @staticmethod
    def is_in_kill_zone(utc_time: datetime.datetime, normalize_tz: bool = False) -> Tuple[bool, str]:
        """
        ICT Kill Zone Filter.
        London Kill Zone: 07:00-11:30 UTC
        NY Kill Zone: 12:30-16:30 UTC
        Asian Session Lockout: 00:00-07:00 UTC
        Rollover / Off-Hours Lockout: 16:30-24:00 UTC or 11:30-12:30 UTC
        """
        if normalize_tz and utc_time.tzinfo is not None:
            utc_time = utc_time.astimezone(datetime.timezone.utc)

        hour_dec = utc_time.hour + (utc_time.minute / 60.0) + (utc_time.second / 3600.0)
        if 7.0 <= hour_dec <= 11.5:
            return True, "LONDON_KILL_ZONE"
        elif 12.5 <= hour_dec <= 16.5:
            return True, "NY_KILL_ZONE"
        elif 0.0 <= hour_dec < 7.0:
            return False, "ASIAN_SESSION_LOCKOUT"
        elif (16.5 < hour_dec <= 24.0) or (11.5 < hour_dec < 12.5):
            return False, "ROLLOVER_OR_OFF_HOURS_LOCKOUT"
        else:
            return False, "OUTSIDE_KILL_ZONE"

    @staticmethod
    def check_volatility_expansion(atr_current: float, atr_sma: float) -> bool:
        """
        Volatility Expansion Filter.
        Avoids low-volatility dead markets where stop-hunts occur frequently.
        """
        if atr_sma <= 0:
            return True
        return (atr_current / atr_sma) >= 0.85
