import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import requests
import json
import time

def run_tests():
    print("================================================================================")
    print("SOVEREIGN AI QUANT ENGINE: COMPREHENSIVE AUTOMATION & SCENARIO TEST")
    print("================================================================================")
    
    # 1. WhatsApp Security & 2-Way Command Automation
    print("\n--- [TEST 1] WhatsApp 2-Way AI Command Automation & Whitelist Security ---")
    commands = [
        ("923468053268", "status"),
        ("923468053268", "forecast BTCUSD"),
        ("923468053268", "forecast XAUUSD"),
        ("923468053268", "weather XAUUSD"),
        ("923468053268", "I have $100 in Binance, give me best 5min scalp position"),
        ("923468053268", "breakeven"),
        ("923468053268", "scale 50%"),
        ("923487117832", "status"), # Blocked contact
        ("923322555238", "buy gold"), # Blocked contact
    ]
    
    for sender, msg in commands:
        try:
            res = requests.post(
                "http://127.0.0.1:5000/api/whatsapp_command",
                json={"from": sender, "body": msg},
                timeout=6
            )
            data = res.json()
            is_blocked = (data.get("status") == "blocked")
            if sender in ["923487117832", "923322555238"]:
                assert is_blocked, f"Failed security whitelist test for {sender}"
                print(f"  [PASS] Blocked Unauthorized Contact: {sender}")
            else:
                assert res.status_code == 200 and not is_blocked
                reply = data.get("reply", "")
                print(f"  [PASS] Authorized Command '{msg[:28]}': Response len={len(reply)} chars")
        except Exception as e:
            print(f"  [FAIL] Command '{msg}' error: {e}")
            raise e

    # 2. Multi-Asset Live Chart Data & Forecast Anchoring
    print("\n--- [TEST 2] Multi-Asset Institutional Forecasting & Liquidation Anchoring ---")
    symbols = ["BTCUSD", "XAUUSD", "EURUSD", "ETHUSD", "SOLUSD"]
    for sym in symbols:
        res = requests.get(f"http://127.0.0.1:5000/api/chart_data/{sym}?tf=M15", timeout=5)
        assert res.status_code == 200
        data = res.json()
        bias = data.get("primary_bias")
        target = data.get("destination_liquidity_target")
        pool = data.get("target_pool_type")
        ghosts = data.get("future_projected_candles", [])
        assert len(ghosts) == 4
        print(f"  [PASS] {sym}: Bias={bias} | Target=${target} ({pool}) | 4 Ghosts OK")

    # 3. 1-Click Execution & Position Risk Actions
    print("\n--- [TEST 3] 1-Click Execution & Risk Modifications (Breakeven, Scale, Close) ---")
    actions = ["breakeven", "scale_50", "trail", "close"]
    for act in actions:
        res = requests.post(
            "http://127.0.0.1:5000/api/execution/action",
            json={"ticket": 9841201, "action": act},
            timeout=5
        )
        assert res.status_code == 200
        data = res.json()
        print(f"  [PASS] Action '{act}': Status={data.get('status')} | {data.get('message')}")

    # 4. Prop Firm Compliance & Fleet Risk Guards
    print("\n--- [TEST 4] Prop Firm Compliance & Aladdin 99% VaR Hard Shield ---")
    from src.funding_pips_expert import FundingPipsExpert
    
    tier_map = {5000: "5k", 25000: "25k", 50000: "50k", 100000: "100k"}
    for bal, t_name in tier_map.items():
        expert = FundingPipsExpert(t_name)
        check = expert.evaluate_phase_progression(current_equity=bal * 1.09, starting_balance=bal)
        assert check["current_phase"] == "PHASE_2_PRACTITIONER"
        assert check["suggested_risk_per_trade_pct"] == 0.50
        print(f"  [PASS] Funding Pips ${bal:,} ({t_name}) Tier: Phase 1 target (+9%) met -> Advanced to Phase 2 (0.50% risk).")

    # 5. Dual-Venue Crypto Connector (Bitget REST & Mark Price)
    print("\n--- [TEST 5] Bitget Crypto Connector & Standardizer ---")
    from src.bitget_connector import BitgetConnector
    bitget = BitgetConnector()
    pos = bitget.get_open_positions()
    print(f"  [PASS] Bitget V2 API: Live positions retrieved ({len(pos)} open positions).")

    print("\n================================================================================")
    print("ALL AUTOMATION SCENARIOS & ENGINE TESTS: 100% PASSED")
    print("================================================================================")

if __name__ == "__main__":
    run_tests()
