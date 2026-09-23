import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
orders = mt5.history_orders_get(datetime(2026, 8, 14, 11, 0, tzinfo=timezone.utc), now)
print(f"Total history orders since 11:00 UTC: {len(orders or [])}")
for o in (orders or []):
    t = datetime.fromtimestamp(o.time_done if o.time_done else o.time_setup, tz=timezone.utc).strftime('%H:%M:%S')
    state_map = {0:"Started", 1:"Placed", 2:"Canceled", 3:"Partial", 4:"Filled", 5:"Rejected", 6:"Expired"}
    state_str = state_map.get(o.state, str(o.state))
    print(f"Order #{o.ticket} | PosID: {o.position_id} | {o.symbol} | Type: {o.type} | Vol: {o.volume_initial} -> {o.volume_current} | Price: {o.price_open} | SL: {o.sl} | TP: {o.tp} | State: {state_str} | Comment: {o.comment} | Time: {t} UTC")

mt5.shutdown()
