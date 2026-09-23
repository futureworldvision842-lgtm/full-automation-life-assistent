import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(hours=24), now)

for d in (deals or []):
    if d.position_id in (57983547458, 57985942149, 57983783202):
        t = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime('%H:%M:%S')
        dr = "BUY" if d.type == 0 else "SELL"
        entry_str = "ENTRY" if d.entry == 0 else "EXIT"
        reason_str = {0:"Client", 3:"Expert Bot", 4:"SL Hit", 5:"TP Hit"}.get(d.reason, str(d.reason))
        print(f"PosID: {d.position_id} | {d.symbol} | {dr} {d.volume} lots | {entry_str} | Price: {d.price:.5f} | Profit: ${d.profit:.2f} | Reason: {reason_str} | Time: {t} UTC")

mt5.shutdown()
