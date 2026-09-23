import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(hours=6), now)

print("\n" + "="*70)
print("  DEAL DETAILS — Last 6 Hours")
print("="*70)

for d in (deals or []):
    t = datetime.fromtimestamp(d.time, tz=timezone.utc).strftime('%H:%M:%S')
    dr = "BUY" if d.type == 0 else "SELL"
    entry_str = "ENTRY (IN)" if d.entry == 0 else ("EXIT (OUT)" if d.entry == 1 else "IN/OUT")
    print(f"  Ticket: {d.ticket} | Pos: {d.position_id} | {d.symbol} | {dr} {d.volume} lots | {entry_str} | Price: {d.price:.5f} | Profit: ${d.profit:.2f} | Reason: {d.reason} | Time: {t} UTC")

print("\n" + "="*70)

# Check EURUSD H1 and M15 candles around the entry and exit time
print("\n  EURUSD M15 Candles (Last 10 bars):")
print(f"  {'Time(UTC)':<12} {'Open':>9} {'High':>9} {'Low':>9} {'Close':>9} {'Move':>8}")
print("  " + "-"*55)
bars_eur = mt5.copy_rates_from_pos("EURUSD", mt5.TIMEFRAME_M15, 0, 10)
if bars_eur is not None:
    for b in bars_eur:
        t = datetime.fromtimestamp(b['time'], tz=timezone.utc).strftime('%H:%M')
        move = (b['close'] - b['open']) / 0.0001
        print(f"  {t:^12} {b['open']:>9.5f} {b['high']:>9.5f} {b['low']:>9.5f} {b['close']:>9.5f} {move:>+7.1f}p")

# Check XAUUSD entry details
print("\n" + "="*70)
print("  CURRENT XAUUSD TRADE DETAILS (Pos: 57985942149)")
print("="*70)
bars_gold = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 10)
if bars_gold is not None:
    for b in bars_gold:
        t = datetime.fromtimestamp(b['time'], tz=timezone.utc).strftime('%H:%M')
        move = b['close'] - b['open']
        print(f"  {t:^12} {b['open']:>9.2f} {b['high']:>9.2f} {b['low']:>9.2f} {b['close']:>9.2f} {move:>+7.2f}")

mt5.shutdown()
