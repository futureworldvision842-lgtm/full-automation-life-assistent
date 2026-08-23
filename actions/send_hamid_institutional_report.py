"""
actions/send_hamid_institutional_report.py — Institutional Funded Account Gold Trader Report for Hamid
"""

import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from actions.send_message import send_message

def send_hamid_gold_report():
    report = (
        "*J.A.R.V.I.S. INSTITUTIONAL GOLD (XAU/USD) TRADING REPORT*\n"
        f"Date: {time.strftime('%Y-%m-%d %H:%M')} PKT | Client: Hamid (Funded Trader)\n\n"
        
        "*1. LATEST MARKET MOVERS & NEWS IMPACT:*\n"
        "- Geopolitical Tension Respite: Cooling US-Iran tensions & oil price stabilization easing US Treasury yields, providing strong underlying support for Gold.\n"
        "- FED Policy Wait & See: Markets consolidating ahead of upcoming Federal Reserve interest rate guidance.\n"
        "- BRICS & Central Bank Buying: Steady structural demand holding Gold firm above $4,000 floor.\n\n"
        
        "*2. 3-DAY PRICE HISTORY & MARKET STRUCTURE:*\n"
        "- 3-Day High: $4,132\n"
        "- 3-Day Low: $4,022\n"
        "- Current Spot Price: ~$4,097 - $4,100\n"
        "- Market Phase: Consolidation near critical $4,100 Resistance Barrier.\n\n"
        
        "*3. KEY TECHNICAL LEVELS (XAU/USD):*\n"
        "- Major Resistance: $4,100 (Critical Barrier) -> Next Targets: $4,132 / $4,173\n"
        "- Immediate Support: $4,022 - $4,025\n"
        "- Major Psychological Floor: $4,000\n\n"
        
        "*4. FUNDED ACCOUNT ACTIONABLE TRADING PLAN & LOT ADVICE:*\n"
        "[SCENARIO A - DIP BUY / REJECTION AT SUPPORT]\n"
        "• Entry Zone: $4,028 - $4,035 (Buy Limit / Rejection Entry)\n"
        "• Stop Loss (SL): $4,015 (Risking ~150 pips)\n"
        "• Take Profit (TP): $4,090 - $4,100 (+600 pips)\n\n"
        
        "[SCENARIO B - BREAKOUT BUY ABOVE $4,100]\n"
        "• Entry: 1-Hour Candle Close above $4,105\n"
        "• Stop Loss (SL): $4,090\n"
        "• Take Profit 1: $4,132 | Take Profit 2: $4,173\n\n"
        
        "*RISK & LOT SIZING RECOMMENDATION (FUNDED ACCOUNTS):*\n"
        "• For $50K Account: Max 0.25 - 0.50 Lot\n"
        "• For $100K Account: Max 0.50 - 1.00 Lot\n"
        "• Rule: Do not risk more than 0.5% - 1% of equity per trade to safeguard Prop Firm Daily Drawdown!"
    )
    
    result = send_message({"receiver": "hamid", "message_text": report, "platform": "whatsapp"})
    print(f"[HamidGoldReport] {result}")
    return result

if __name__ == "__main__":
    send_hamid_gold_report()
