import MetaTrader5 as mt5
mt5.initialize()
positions = mt5.positions_get()
if positions:
    print(f"\n{'='*65}")
    print(f"  LIVE OPEN POSITIONS — MT5 Account #{mt5.account_info().login}")
    print(f"{'='*65}")
    for p in positions:
        direction = "BUY " if p.type == 0 else "SELL"
        rr = abs(p.tp - p.price_open) / abs(p.price_open - p.sl) if p.sl and p.tp and abs(p.price_open - p.sl) > 0 else 0
        print(f"  Ticket : {p.ticket}")
        print(f"  Symbol : {p.symbol}  |  {direction}  |  Vol: {p.volume}")
        print(f"  Entry  : {p.price_open:.5f}  |  Current: {p.price_current:.5f}")
        print(f"  SL     : {p.sl:.5f}  |  TP: {p.tp:.5f}  |  R:R {rr:.1f}")
        print(f"  Profit : ${p.profit:.2f}  |  Comment: {p.comment}")
        print(f"  {'-'*61}")
    acc = mt5.account_info()
    print(f"\n  Balance: ${acc.balance:.2f}  |  Equity: ${acc.equity:.2f}  |  Floating: ${acc.profit:.2f}")
    print(f"  Total Open: {len(positions)} trade(s)")
    print(f"{'='*65}\n")
else:
    print("No open positions currently.")
mt5.shutdown()
