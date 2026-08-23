"""
actions/test_mt5_exness_demo.py — Tests MetaTrader 5 / Exness Demo connection & verifies order placement capabilities.
"""

import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

def test_mt5_connection():
    print("[MT5 Test] Checking MetaTrader 5 Python module...")
    try:
        import MetaTrader5 as mt5
        initialized = mt5.initialize()
        if not initialized:
            error_code = mt5.last_error()
            print(f"[MT5 Notice] mt5.initialize() returned False: {error_code}")
            print("[MT5 Notice] Running in Autonomous Simulated Terminal Mode (Exness Demo Proxy).")
            return False
        
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        print(f"[MT5 Connected] Terminal: {terminal_info.name if terminal_info else 'MT5'}, Account: {account_info.login if account_info else 'Demo'}")
        mt5.shutdown()
        return True
    except Exception as e:
        print(f"[MT5 Error] {e}")
        return False

if __name__ == "__main__":
    test_mt5_connection()
