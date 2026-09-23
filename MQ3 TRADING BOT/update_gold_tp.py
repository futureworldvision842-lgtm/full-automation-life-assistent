import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5

mt5.initialize()
positions = mt5.positions_get(symbol="XAUUSD")

if positions:
    for p in positions:
        print(f"Current Position: #{p.ticket} {p.symbol} | SL: {p.sl} | Old TP: {p.tp}")
        # Update TP to real structural psychological level $4350.50 (instead of arbitrary 4338.85)
        new_tp = 4350.50
        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": p.ticket,
            "symbol": p.symbol,
            "sl": p.sl,
            "tp": new_tp
        }
        res = mt5.order_send(req)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"SUCCESS: Position #{p.ticket} TP updated to REAL Structural Level ${new_tp:.2f}")
        else:
            print(f"Note: retcode={res.retcode if res else 'None'} ({res.comment if res else ''})")
else:
    print("No open XAUUSD position found.")

mt5.shutdown()
