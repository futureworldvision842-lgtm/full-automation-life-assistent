import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get()
print(f"Total Open Positions: {len(positions or [])}")
for p in (positions or []):
    print(f"Ticket: {p.ticket} | Symbol: {p.symbol} | Type: {'BUY' if p.type==0 else 'SELL'} | Vol: {p.volume} | Open: {p.price_open} | Cur: {p.price_current} | SL: {p.sl} | TP: {p.tp} | Profit: ${p.profit:.2f}")

orders = mt5.orders_get()
print(f"Total Pending Orders: {len(orders or [])}")
for o in (orders or []):
    print(f"Order #{o.ticket} | {o.symbol} | Type: {o.type} | Vol: {o.volume_current} | Price: {o.price_open}")

mt5.shutdown()
