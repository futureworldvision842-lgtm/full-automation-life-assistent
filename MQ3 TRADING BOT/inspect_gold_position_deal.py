import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
deals = mt5.history_deals_get(position=57988428151)

print(f"Deals for Position #57988428151: {len(deals or [])}")
for d in (deals or []):
    t = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime('%H:%M:%S')
    dr = "BUY" if d.type == 0 else "SELL"
    entry_str = "ENTRY" if d.entry == 0 else ("EXIT" if d.entry == 1 else "IN/OUT")
    reason_str = {0:"Client", 1:"Mobile", 2:"Web", 3:"Bot", 4:"SL Hit", 5:"TP Hit", 6:"Stop Out"}.get(d.reason, str(d.reason))
    print(f"Ticket: {d.ticket} | {d.symbol} | {dr} {d.volume} lots | {entry_str} | Price: {d.price} | Profit: ${d.profit:.2f} | Reason: {reason_str} | Time: {t} UTC")

mt5.shutdown()
