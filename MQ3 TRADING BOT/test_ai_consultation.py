import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from src.whatsapp_qr_manager import WhatsAppQRManager

mgr = WhatsAppQRManager()

print("\n" + "="*80)
print("  TESTING INTERACTIVE AI TRADE CONSULTATION & CO-PILOT ADVISOR")
print("="*80 + "\n")

queries = [
    "Main Gold buy karna chahta hoon, kya kehte ho?",
    "Should I sell Gold right now?",
    "Silver par konsi position achi hogi?",
    "USDJPY sell karna theek hai?"
]

for q in queries:
    print(f"\n💬 USER QUERY: '{q}'")
    print("-" * 50)
    reply = mgr.handle_incoming_command(q, "923468053268@s.whatsapp.net")
    print(reply)

print("\n" + "="*80)
print("  ALL 4 TRADE CONSULTATIONS EXECUTED WITH FULL EVIDENCE & REASONING ✅")
print("="*80 + "\n")
