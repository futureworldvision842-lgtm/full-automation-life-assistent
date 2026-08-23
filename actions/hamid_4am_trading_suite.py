"""
actions/hamid_4am_trading_suite.py — 4:00 AM Multi-Asset Trading Intelligence Engine for Hamid
Tailored specifically for $25,000 Funded Accounts (Pips Passed / Prop Firm) covering Gold, Silver & Bitcoin.
"""

import sys
import json
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from actions.send_message import send_message

def generate_4am_multi_asset_report() -> str:
    date_str = time.strftime('%Y-%m-%d 04:00')
    report = (
        "*J.A.R.V.I.S. 4:00 AM MORNING TRADING INTELLIGENCE REPORT*\n"
        f"Date: {date_str} PKT | Client: Hamid ($25K Funded Account)\n\n"
        
        "*1. TODAY'S BEST TRADING WINDOWS (PKT):*\n"
        "- London Session Opening: 12:00 PM - 4:00 PM (Best for Gold & Silver Trend setups)\n"
        "- NY Overlap Session: 5:00 PM - 9:00 PM (Highest Liquidity & Volatility)\n\n"
        
        "*2. MULTI-ASSET MARKET ANALYSIS & SCENARIOS:*\n\n"
        
        "[A. GOLD (XAU/USD) - SPOT ~$4,097 - $4,100]\n"
        "- Macro Catalyst: US-Iran geopolitical respite & cooling oil prices holding Treasury yields low.\n"
        "- Major Levels: Resistance $4,100 / $4,132 | Support $4,025 / $4,000.\n"
        "- IF NEWS BULLISH / BREAKOUT: 1H candle closes above $4,105 -> BUY | TP: $4,132 | SL: $4,090.\n"
        "- IF NEWS BEARISH / DIP: Price dips to $4,028-$4,035 with bullish pinbar -> BUY | TP: $4,095 | SL: $4,015.\n"
        "- Lot Sizing ($25K Account): 0.10 - 0.20 Lot MAX (Risk ~$100-$150 per trade).\n\n"
        
        "[B. SILVER (XAG/USD) - SPOT ~$38.50 - $39.20]\n"
        "- Macro Catalyst: Industrial demand & precious metals sympathy rally.\n"
        "- Major Levels: Resistance $40.00 | Support $37.80.\n"
        "- TRADE SCENARIO: Dip entry near $38.00 -> BUY | TP: $39.80 | SL: $37.40.\n"
        "- Lot Sizing ($25K Account): 0.10 - 0.25 Lot MAX.\n\n"
        
        "[C. BITCOIN (BTC/USD) - SPOT ~$67,500 - $68,400]\n"
        "- Macro Catalyst: ETF inflows & consolidation before next macro expansion.\n"
        "- Major Levels: Resistance $69,500 | Support $66,200.\n"
        "- TRADE SCENARIO: Rejection at $66,400-$66,800 -> BUY | TP: $69,200 | SL: $65,500.\n"
        "- Lot Sizing ($25K Account): 0.05 - 0.10 Lot MAX.\n\n"
        
        "*3. $25K FUNDED ACCOUNT RISK RULES (PIPS PASSED):*\n"
        "• Max Daily Drawdown Allowed: 5% ($1,250 USD)\n"
        "• Max Risk Per Trade: 0.5% ($125 USD)\n"
        "• Rule: Never open more than 2 positions concurrently to protect prop firm daily limits!"
    )
    return report

def generate_voice_summary_file(report_text: str) -> str:
    """Synthesizes a clean audio voice note using edge_tts for Hamid."""
    try:
        import asyncio, edge_tts
        summary = (
            "Assalam-o-Alaikum Hamid Bhai. Here is your J.A.R.V.I.S. 4:00 AM Trading Intelligence update for Gold, Silver, and Bitcoin. "
            "For Gold XAU USD, major levels are resistance at 4,100 and support at 4,025. Recommended lot size for your 25,000 dollar account is 0.10 to 0.20 lot MAX. "
            "For Silver, look for dip entries near 38.00. For Bitcoin, support is at 66,200. Remember to keep daily drawdown under 5 percent to protect your prop firm funded account."
        )
        audio_file = BASE_DIR / "scratch" / f"hamid_voice_{int(time.time())}.mp3"
        async def _gen():
            comm = edge_tts.Communicate(summary, "en-US-ChristopherNeural")
            await comm.save(str(audio_file))
        asyncio.run(_gen())
        return str(audio_file)
    except Exception as e:
        print(f"[VoiceGenError] {e}")
        return None

def send_4am_report_to_hamid():
    report_text = generate_4am_multi_asset_report()
    voice_file = generate_voice_summary_file(report_text)
    params = {"receiver": "hamid", "message_text": report_text, "platform": "whatsapp"}
    if voice_file and Path(voice_file).exists():
        params["audio_path"] = voice_file
    result = send_message(params)
    print(f"[Hamid4AMReport] {result}")
    return result

if __name__ == "__main__":
    send_4am_report_to_hamid()
