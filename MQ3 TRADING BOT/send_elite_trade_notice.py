import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

msg = (
    "🏛️ *OFFICIAL NOTICE: ELITE TRADE EXCLUSIVE HUB ACTIVE!* 🟢\n"
    "═════════════════════════════\n"
    "Tamam institutional broadcasts, daily morning playbooks, intraday A+ alerts aur nightly retrospectives ab *SIRF AUR SIRF* is group mein post honge!\n\n"
    "💬 *Group Two-Way AI Co-Pilot Active:*\n"
    "Is group mein jab bhi koi member sawal poochega ya commands likhega, bot foran is group mein institutional jawab dega:\n\n"
    "• `status` — Live Account & Equity Telemetry\n"
    "• `morning` — Subah Ka Pre-Market Master Playbook\n"
    "• `gold` / `xauusd` — Live Gold SMC Analysis & Levels\n"
    "• `trades` — Open Running Positions\n"
    "• `fleet` — 4-Account Portfolio Allocations ($100k, $50k, $25k, $5k)\n"
    "• `night` — Nightly Retrospective & Win/Loss Audit\n"
    "• `Main Gold buy karna chahta hoon` — Real-Time Trade Consultation\n\n"
    "🚀 *Trading Bot 24/7 autonomous risk shield par active hai!*"
)

r = requests.post("http://127.0.0.1:3001/send_group", json={
    "group_name": "Elite Trade",
    "message": msg
}, timeout=10)

print("Dispatch Response:", r.json())
