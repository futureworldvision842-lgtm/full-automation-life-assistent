import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
# Last 3 days
deals = mt5.history_deals_get(now - timedelta(days=3), now)
print(f"Total deals found: {len(deals or [])}")
for d in (deals or []):
    t = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    dr = "BUY" if d.type == 0 else "SELL"
    entry_str = "IN" if d.entry == 0 else "OUT"
    reason_str = {0:"Client", 3:"Bot", 4:"SL Hit", 5:"TP Hit"}.get(d.reason, str(d.reason))
    print(f"PosID: {d.position_id} | {d.symbol} | {dr} {d.volume} lots | {entry_str} | Price: {d.price:.5f} | Profit: ${d.profit:.2f} | Reason: {reason_str} | Time: {t}")

mt5.shutdown()
