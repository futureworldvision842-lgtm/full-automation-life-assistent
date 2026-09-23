import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(hours=24), now)
positions = {}
for d in (deals or []):
    pid = d.position_id
    if pid not in positions:
        positions[pid] = []
    positions[pid].append(d)

total_profit = 0.0
wins = 0
losses = 0

print("\n" + "="*65)
print("  CLOSED TRADE HISTORY -- Last 24 Hours")
print("  Account #" + str(mt5.account_info().login))
print("="*65)

for pid, dl in positions.items():
    entry = next((d for d in dl if d.entry == 0), None)
    exits = [d for d in dl if d.entry == 1]
    if not entry:
        continue

    sym = entry.symbol
    vol = entry.volume
    ep  = entry.price
    et  = datetime.fromtimestamp(entry.time, tz=timezone.utc).strftime('%H:%M:%S')
    dr  = "BUY" if entry.type == 0 else "SELL"
    cmt = entry.comment or ""

    xp  = exits[-1].price if exits else 0.0
    xt  = datetime.fromtimestamp(exits[-1].time, tz=timezone.utc).strftime('%H:%M:%S') if exits else "--"
    pnl = sum(d.profit + d.swap + d.commission for d in exits) if exits else 0.0

    mult = 0.0001 if sym not in ["XAUUSD", "USDJPY"] else (0.01 if sym == "USDJPY" else 0.1)
    raw_pips = ((xp - ep) if dr == "BUY" else (ep - xp)) if exits else 0.0
    pips = raw_pips / mult

    res = "WIN" if pnl > 0 else ("LOSS" if pnl < 0 else "OPEN")

    if exits:
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
        total_profit += pnl

    print(f"\n  Position   : #{pid}")
    print(f"  Symbol     : {sym}  |  {dr}  |  {vol} lots")
    print(f"  Entry Time : {et} UTC  ->  Entry Price : {ep:.5f}")
    print(f"  Exit Time  : {xt} UTC  ->  Exit  Price : {xp:.5f}")
    print(f"  Pips       : {pips:+.1f}")
    print(f"  Profit     : ${pnl:.2f}  |  Result : {res}")
    if cmt:
        print(f"  Comment    : {cmt}")
    print("  " + "-"*61)

acc = mt5.account_info()
total = wins + losses
wr = f"{wins/total*100:.0f}%" if total > 0 else "N/A"
print(f"\n  SUMMARY:")
print(f"  Trades   : {total}  |  Wins : {wins}  |  Losses : {losses}  |  Win Rate : {wr}")
print(f"  Total P&L: ${total_profit:+.2f}")
print(f"  Balance  : ${acc.balance:.2f}  |  Equity : ${acc.equity:.2f}")
print("="*65 + "\n")
mt5.shutdown()
