import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5

mt5.initialize()
positions = mt5.positions_get(symbol="XAUUSD")

if positions:
    for p in positions:
        print(f"Current Position: #{p.ticket} {p.symbol} | SL: {p.sl} | Old TP: {p.tp}")
        # Update TP strictly to REAL CHART Bullish Order Block High @ $4353.80
        new_tp = 4353.80
        req = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": p.ticket,
            "symbol": p.symbol,
            "sl": p.sl,
            "tp": new_tp
        }
        res = mt5.order_send(req)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"SUCCESS: Position #{p.ticket} TP updated to REAL CHART Bullish Order Block High @ ${new_tp:.2f}")
        else:
            print(f"Note: retcode={res.retcode if res else 'None'} ({res.comment if res else ''})")
else:
    print("No open XAUUSD position found.")

mt5.shutdown()
