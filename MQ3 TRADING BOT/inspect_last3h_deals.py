import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(hours=3), now)

print("\n" + "="*80)
print(f"  ALL DEALS IN MT5 (LAST 3 HOURS) — Total Deals: {len(deals or [])}")
print("="*80)

for d in (deals or []):
    t = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime('%H:%M:%S')
    dr = "BUY" if d.type == 0 else "SELL"
    entry_str = "ENTRY" if d.entry == 0 else ("EXIT" if d.entry == 1 else "IN/OUT")
    reason_str = {0:"Client", 1:"Mobile", 2:"Web", 3:"Bot", 4:"SL Hit", 5:"TP Hit", 6:"Stop Out"}.get(d.reason, str(d.reason))
    print(f"Ticket: {d.ticket:<12} | Pos: {d.position_id:<12} | {d.symbol:<6} | {dr:<4} {d.volume:>5.2f} lots | {entry_str:<5} | Price: {d.price:>9.5f} | Profit: ${d.profit:>8.2f} | Reason: {reason_str:<8} | Time: {t} UTC")

mt5.shutdown()
