import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

mt5.initialize()

now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(hours=48), now)

print("\n" + "="*68)
print("  XAUUSD GOLD TRADE FORENSIC — SL Hit Analysis")
print("="*68)

target_position = 57971249654
entry_price = 0.0
exit_price  = 0.0
entry_time  = None
exit_time   = None
exit_reason = ""

reason_map = {0:"Manual",1:"Mobile",2:"Web",3:"Expert Bot",4:"SL HIT",5:"TP HIT",6:"Stop Out"}

for d in (deals or []):
    if d.position_id == target_position:
        t = datetime.fromtimestamp(d.time, tz=timezone.utc)
        kind = "ENTRY" if d.entry == 0 else "EXIT"
        reason = reason_map.get(d.reason, str(d.reason))
        print(f"\n  [{kind}]  Time: {t.strftime('%H:%M:%S')} UTC")
        print(f"  Price  : {d.price:.2f}   Volume: {d.volume} lots")
        print(f"  Profit : ${d.profit:.2f}   Reason: {reason}")
        print(f"  Comment: {d.comment}")
        if d.entry == 0:
            entry_price = d.price
            entry_time  = t
        else:
            exit_price  = d.price
            exit_time   = t
            exit_reason = reason

print("\n" + "-"*68)
if entry_price and exit_price:
    drop = entry_price - exit_price
    duration = (exit_time - entry_time).seconds // 60 if exit_time and entry_time else 0
    print(f"\n  TRADE SUMMARY:")
    print(f"  Entry       : ${entry_price:.2f}  at {entry_time.strftime('%H:%M') if entry_time else '?'} UTC")
    print(f"  Exit        : ${exit_price:.2f}   at {exit_time.strftime('%H:%M') if exit_time else '?'} UTC")
    print(f"  Gold Dropped: ${drop:.2f}  in {duration} minutes")
    print(f"  Exit Reason : {exit_reason}")

# H1 candles around trade time
print(f"\n  XAUUSD H1 Price Action (13 Aug 17:00-21:00 UTC):")
print(f"  {'Time':^10} {'Open':^10} {'High':^10} {'Low':^10} {'Close':^10} {'Candle':^12}")
print(f"  {'-'*60}")

bars = mt5.copy_rates_from("XAUUSD", mt5.TIMEFRAME_H1,
                            datetime(2026, 8, 13, 17, 0, tzinfo=timezone.utc), 6)
if bars is not None:
    for b in bars:
        t = datetime.fromtimestamp(b['time'], tz=timezone.utc).strftime('%H:%M')
        move = b['close'] - b['open']
        candle = "BULLISH" if move > 0 else "BEARISH"
        marker = ""
        if t == "18:00": marker = " <-- BOT ENTRY"
        if t == "19:00": marker = " <-- CRASH HERE"
        print(f"  {t:^10} {b['open']:^10.2f} {b['high']:^10.2f} {b['low']:^10.2f} {b['close']:^10.2f} {move:^+8.2f} {candle}{marker}")

# Current ATR
recent = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 20)
if recent is not None:
    trs = [max(recent[i]['high']-recent[i]['low'],
               abs(recent[i]['high']-recent[i-1]['close']),
               abs(recent[i]['low'] -recent[i-1]['close']))
           for i in range(1, len(recent))]
    atr = sum(trs[-14:]) / 14
    print(f"\n  Current Gold ATR(14) H1 : ${atr:.2f}")
    print(f"  Bot SL was 1.5x ATR     : ~${1.5*atr:.2f} (agar aaj hota)")
    print(f"  Actual drop was         : ~$30 (much larger than SL)")

tick = mt5.symbol_info_tick("XAUUSD")
if tick:
    print(f"  Gold Price Right Now    : ${tick.bid:.2f}")

print("\n" + "="*68)
mt5.shutdown()
