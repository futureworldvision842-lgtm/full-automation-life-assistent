import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.whatsapp_qr_manager import WhatsAppQRManager

broadcaster = CommunitySignalBroadcaster()

print("\n" + "="*80)
print("  GENERATING INSTITUTIONAL COMMUNITY SIGNAL CARD & BROADCASTING")
print("="*80 + "\n")

card = broadcaster.format_community_signal_card(
    symbol="XAUUSD",
    signal_type="BUY",
    entry_price=4376.50,
    sl_price=4364.50,
    tp1_price=4396.60,
    tp2_price=4410.00,
    analysis={
        "trend_direction": "BULLISH",
        "confluence_score": 5.3,
        "ote_buy": {"in_ote_zone": True},
        "intermarket_intel": {
            "dxy_trend": "BEARISH",
            "macro_regime": "RISK_OFF_GOLD_SURGE"
        }
    },
    sl_pips=120.0
)

print(card)
print("\n" + "-"*80)
print("Dispatching to Authorized Master Owner Contact...")

results = broadcaster.broadcast_signal(card)
for contact, ok in results.items():
    print(f"✔ Broadcast to {contact} -> Status: {'DELIVERED ✅' if ok else 'FAILED ❌'}")

print("\n" + "="*80)
print("  COMMUNITY BROADCAST COMPLETE ✅")
print("="*80 + "\n")
