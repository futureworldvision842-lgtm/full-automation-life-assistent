import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json

from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine

mt5.initialize()

print("\n" + "="*70)
print("  XAUUSD GOLD — 4310/4315 Miss Analysis (Aaj Subha)")
print("="*70)

with open("config.json") as f:
    cfg = json.load(f)

analyzer = MarketAnalyzer(cfg)
strategy = StrategyEngine(cfg)

# Fetch H1 and M15 bars
bars_h1 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 30)
bars_m15 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 100)

df_h1 = pd.DataFrame(bars_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')

df_m15 = pd.DataFrame(bars_m15)
df_m15['time'] = pd.to_datetime(df_m15['time'], unit='s')

print("\n  XAUUSD H1 Candles — Today:")
print(f"  {'Time (UTC)':<18} {'Open':>9} {'High':>9} {'Low':>9} {'Close':>9} {'Move':>8}")
print("  " + "-"*65)

for _, row in df_h1.tail(15).iterrows():
    t_str = row['time'].strftime('%Y-%m-%d %H:%M')
    move = row['close'] - row['open']
    print(f"  {t_str:<18} {row['open']:>9.2f} {row['high']:>9.2f} {row['low']:>9.2f} {row['close']:>9.2f} {move:>+8.2f}")

print("\n" + "-"*70)
print("  Evaluating Strategy at each M15 candle when Low was near 4310-4320:")
print("-" * 70)

# Simulate what the analyzer + strategy saw at past M15 bars
for i in range(20, len(df_m15)):
    sub_m15 = df_m15.iloc[:i+1]
    last_bar = sub_m15.iloc[-1]
    if last_bar['low'] <= 4325:
        # Find corresponding H1 slice
        cur_time = last_bar['time']
        sub_h1 = df_h1[df_h1['time'] <= cur_time]
        if len(sub_h1) < 20:
            continue
        
        analysis = analyzer.analyze_symbol("XAUUSD", sub_h1, sub_m15)
        sig = strategy.evaluate_signals(analysis)
        
        t_str = cur_time.strftime('%Y-%m-%d %H:%M')
        trend = analysis.get("trend_direction")
        rsi = analysis.get("rsi")
        sweep = analysis.get("liquidity_sweep", {}).get("type")
        fvg = "YES" if analysis.get("bullish_fvg") else "NO"
        ob = "YES" if analysis.get("bullish_ob") else "NO"
        
        print(f"\n  Time: {t_str} UTC | Price: {last_bar['close']:.2f} (Low: {last_bar['low']:.2f})")
        print(f"    H1 Trend: {trend} | M15 RSI: {rsi:.1f} | Sweep: {sweep} | Bullish FVG: {fvg} | Bullish OB: {ob}")
        if sig:
            print(f"    >>> SIGNAL GENERATED: {sig['signal']} | Score reason: {sig.get('reason')}")
        else:
            print(f"    >>> NO SIGNAL. Reason details:")
            # Detail why
            if trend == "BEARISH" and sweep != "BULLISH_SWEEP" and analysis.get("structure_pattern") != "DOUBLE_BOTTOM":
                print(f"        -> Trend was BEARISH on H1 and no Bullish Liquidity Sweep / Double Bottom detected yet!")
            elif rsi < 30 or rsi > 68:
                print(f"        -> RSI was outside [30, 68] window: {rsi:.1f}")
            else:
                print(f"        -> Insufficient confluence score or criteria not met.")

mt5.shutdown()
