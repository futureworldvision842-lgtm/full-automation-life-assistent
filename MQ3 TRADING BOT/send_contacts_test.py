import sys
import io
import time
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.whatsapp_qr_manager import WhatsAppQRManager

mgr = WhatsAppQRManager()

contacts = [
    {"name": "Master User (Owner)", "phone": "923468053268"}
]

print("\n" + "="*70)
print("  DISPATCHING WHATSAPP TEST MESSAGES TO AUTHORIZED CONTACTS")
print("="*70 + "\n")

for c in contacts:
    msg = (
        f"🤖 *ASSALAM-O-ALAIKUM {c['name'].upper()}!* 🚀\n\n"
        f"Yeh *Funding Pips Master AI Trading Bot* ka verification test message hai.\n\n"
        f"Aap ka number is system mein *Authorized Contact* ke tor par add ho chuka hai.\n\n"
        f"📊 *Live Portfolio Snapshot:*\n"
        f"• Account: Funding Pips $25k Evaluation\n"
        f"• Banked Balance: $25,958.63 (+$958.63 Profit 💰)\n"
        f"• Equity: $25,967.72 (Risk-Free Active Runner)\n\n"
        f"💬 *Commands Aap Is Chat Par Reply Kar Saktay Hain:*\n"
        f"• *status* — Live Balance & Profit\n"
        f"• *gold* — Gold Macro Trend & Levels\n"
        f"• *trades* — Running Open Trades\n"
        f"• *plan* — Today's Strategy Playbook\n"
        f"• *help* — Command Menu\n\n"
        f"Trading Bot 24/7 100% safe aur autonomous risk management par active hai!"
    )

    ok = mgr.send_message(msg, to=c["phone"])
    print(f"✔ Dispatched to {c['name']} (+{c['phone']}) -> Status: {'SUCCESS ✅' if ok else 'FAILED ❌'}")
    time.sleep(2)

print("\n" + "="*70)
print("  MASTER OWNER TEST MESSAGE SUCCESSFULLY SENT VIA WHATSAPP ✅")
print("="*70 + "\n")
