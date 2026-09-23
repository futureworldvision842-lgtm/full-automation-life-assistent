"""
market_maker_game_mastery.py — Institutional Market Maker Games, Money Mechanics & Psychology Master Engine.
Encapsulates deep institutional market mechanics, prop firm business models, big shark liquidity traps, and behavioral discipline.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("MarketMakerMastery")


class MarketMakerGameMastery:
    """
    Institutional Market Maker Games, Money Mechanics & Psychology Knowledge Base.
    """

    @staticmethod
    def get_market_mechanics_intelligence() -> Dict[str, Any]:
        return {
            "big_sharks_liquidity_model": {
                "name": "Institutional Order Absorption & Stop-Hunt Engineering",
                "core_mechanism": (
                    "Central banks, tier-1 liquidity providers (JPMorgan, Citadel, Deutsche Bank) cannot enter "
                    "multi-million dollar positions at market price without massive slippage. They intentionally "
                    "engineer retail chart patterns (Double Tops, Support Trendlines, Equal Highs) to build large "
                    "clusters of retail Stop-Loss orders. Once liquidity pools are ripe, they execute aggressive "
                    "sweep wicks (Judas Swings) to trigger retail stops, absorbing that liquidity to enter their true directional positions."
                ),
                "tactical_defense": "Never enter on initial breakout; enter on the retest of the swept Order Block in the 70.5% OTE discount zone."
            },
            "prop_firm_business_model_defense": {
                "name": "Prop Firm B-Book & Trailing Drawdown Traps",
                "core_mechanism": (
                    "Proprietary firms (Funding Pips, FTMO) design evaluation rules to exploit human psychology. "
                    "The primary killer is Trailing Drawdown on floating equity. If a trade floats up +$1,000, "
                    "the drawdown floor ratchets up. If the trade pulls back to breakeven, the account loses $1,000 of drawdown buffer. "
                    "Additionally, spread expansion during 21:00-22:00 UTC rollover triggers overnight stops."
                ),
                "tactical_defense": (
                    "1. Always scale out 50% profit at TP1 to lock hard cash into balance.\n"
                    "2. Move SL to Breakeven (+1 pip) once 1:1 R:R distance is achieved.\n"
                    "3. De-risk lot sizing by 50% once daily target ($400+) is achieved."
                )
            },
            "intermarket_hierarchy": {
                "gold_sovereign_status": "Gold (XAUUSD) is the sovereign global store of value. It moves inversely to real yields and DXY.",
                "silver_beta_multiplier": "Silver (XAGUSD) is Gold's high-beta companion. When Gold breaks out, Silver often lags briefly and then explodes violently with 1.5x - 2.0x higher percentage velocity.",
                "dxy_inverse_anchor": "DXY weakness directly triggers global commodity & precious metals expansion."
            },
            "behavioral_psychology_shield": {
                "loss_aversion_bias": "Losses hurt 2.25x more than gains feel good, leading traders to revenge trade. Bot enforces mandatory 10-min cooldown after a loss.",
                "profit_euphoria_trap": "Traders give back daily profits by over-trading after a winning streak. Bot scales risk down to 0.25% after daily profit target."
            }
        }
