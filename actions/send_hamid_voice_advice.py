"""
actions/send_hamid_voice_advice.py — Generates and sends a rich Neural Voice Note to Hamid via WhatsApp
"""

import sys
import time
import asyncio
import edge_tts
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from actions.send_message import send_message

def generate_voice_advice() -> str:
    audio_path = BASE_DIR / "scratch" / f"hamid_trading_advice_{int(time.time())}.mp3"
    
    advice_script = (
        "Assalam-o-Alaikum Hamid Bhai. Here is your J.A.R.V.I.S. High-Probability Trading Advice for today. "
        "First, for Gold XAU USD: Market is consolidating near 4,097 to 4,100 dollars. Major resistance sits at 4,100 and 4,132. Support is strong at 4,025. "
        "If price breaks above 4,105 on a 1-hour candle, look for a long entry towards 4,132. Alternatively, if price dips to 4,028 to 4,035 with a bullish rejection pinbar, buy with stop-loss below 4,015. "
        "For your 25,000 dollar funded account, strictly use 0.10 to 0.20 lot MAX on Gold to keep your daily risk under 0.5 percent and protect your 5 percent drawdown limit. "
        "Second, for Silver XAG USD: Support is near 38.00 dollars. Look for long entries on pullbacks with target 39.80. "
        "Third, for Bitcoin BTC USD: Support is holding at 66,200. "
        "Best execution windows today are London Session opening between 12:00 PM and 4:00 PM PKT, and New York Overlap from 5:00 PM to 9:00 PM PKT. Wish you profitable trades today, Hamid Bhai!"
    )
    
    async def _synth():
        communicate = edge_tts.Communicate(advice_script, "en-US-ChristopherNeural")
        await communicate.save(str(audio_path))
        
    asyncio.run(_synth())
    return str(audio_path)

def send_voice_advice_to_hamid():
    print("[HamidVoiceAdvice] Synthesizing natural neural voice note...")
    audio_file = generate_voice_advice()
    
    text_caption = (
        "*J.A.R.V.I.S. VOICE TRADING ADVICE FOR HAMID*\n"
        "🎙️ *Audio Voice Note Attached Above*\n\n"
        "• *Gold (XAU/USD)*: Key Resistance $4,100 | Support $4,025 | Max Lot: 0.10 - 0.20\n"
        "• *Silver (XAG/USD)*: Dip Buy near $38.00 | Target $39.80\n"
        "• *Bitcoin (BTC/USD)*: Support $66,200 | Target $69,200\n"
        "• *Risk Rule ($25K Account)*: Keep max risk under 0.5% ($125 USD) per trade."
    )
    
    result = send_message({
        "receiver": "hamid",
        "message_text": text_caption,
        "platform": "whatsapp",
        "audio_path": audio_file
    })
    
    print(f"[HamidVoiceAdvice Result] {result}")
    return result

if __name__ == "__main__":
    send_voice_advice_to_hamid()
