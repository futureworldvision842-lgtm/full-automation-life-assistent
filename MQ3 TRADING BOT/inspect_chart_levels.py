import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import MetaTrader5 as mt5
import pandas as pd
from src.market_analyzer import MarketAnalyzer
import json

with open("config.json", "r") as f:
    config = json.load(f)

mt5.initialize()
analyzer = MarketAnalyzer(config)

rates_h1 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_H1, 0, 100)
rates_m15 = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 0, 60)

df_h1 = pd.DataFrame(rates_h1)
df_m15 = pd.DataFrame(rates_m15)

analysis = analyzer.analyze_symbol("XAUUSD", df_h1, df_m15)

print("\n" + "="*70)
print(f"  REAL CHART TECHNICAL STRUCTURE ANALYSIS FOR XAUUSD (Price: ${analysis['current_price']:.2f})")
print("="*70)

print("\n--- DETECTED REAL CHART SUPPORTS (BELOW PRICE) ---")
for item in analysis["support_levels"]:
    s_lvl, s_lbl = item
    if s_lvl < analysis["current_price"]:
        dist = analysis["current_price"] - s_lvl
        print(f"  Level: ${s_lvl:>7.2f}  |  Distance: -${dist:>5.2f}  |  Source: {s_lbl}")

print("\n--- DETECTED REAL CHART RESISTANCES (ABOVE PRICE) ---")
for item in analysis["resistance_levels"]:
    r_lvl, r_lbl = item
    if r_lvl > analysis["current_price"]:
        dist = r_lvl - analysis["current_price"]
        print(f"  Level: ${r_lvl:>7.2f}  |  Distance: +${dist:>5.2f}  |  Source: {r_lbl}")

if analysis.get("bullish_ob"):
    print(f"\nBullish Order Block on Chart: High=${analysis['bullish_ob']['high']:.2f}, Low=${analysis['bullish_ob']['low']:.2f}")

if analysis.get("bearish_ob"):
    print(f"\nBearish Order Block on Chart: High=${analysis['bearish_ob']['high']:.2f}, Low=${analysis['bearish_ob']['low']:.2f}")

mt5.shutdown()
