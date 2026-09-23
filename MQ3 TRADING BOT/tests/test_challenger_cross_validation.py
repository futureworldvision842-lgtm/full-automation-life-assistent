"""
test_challenger_cross_validation.py — Python-Node Cross-Validation and Empirical Verification.
"""

import os
import sys
import math
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aladdin_risk_engine import AladdinRiskEngine
from src.funding_pips_expert import FundingPipsExpert

class TestCrossValidation(unittest.TestCase):
    def setUp(self):
        self.aladdin = AladdinRiskEngine()
        self.expert_25k = FundingPipsExpert("25k")

    def test_var_cvar_mathematical_constants(self):
        """Cross-validate normal quantiles and PDF multipliers."""
        z_99 = 2.326348
        z_95 = 1.644854
        
        pdf_z99 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * z_99 * z_99)
        pdf_z95 = (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * z_95 * z_95)
        
        phi_over_001 = pdf_z99 / 0.01
        phi_over_005 = pdf_z95 / 0.05
        
        ratio_99 = phi_over_001 / z_99
        ratio_95 = phi_over_005 / z_95
        
        # Cross check against JS constants
        self.assertAlmostEqual(phi_over_001, 2.665214, places=5)
        self.assertAlmostEqual(phi_over_005, 2.062714, places=5)
        self.assertAlmostEqual(ratio_99, 1.145664, places=5) # 14.57%
        self.assertAlmostEqual(ratio_95, 1.254041, places=5) # 25.40%

    def test_trailing_floor_trajectory_funding_pips(self):
        """Cross validate trajectory $25k -> $24.5k -> $26k -> $25.5k -> $27k -> $24k."""
        expert = FundingPipsExpert("25k")
        # Step 1: Initial $25k
        self.assertEqual(expert.absolute_high_watermark, 25000.0)
        
        # Step 2: $24.5k
        expert.update_daily_watermark(equity=24500.0, balance=25000.0)
        self.assertEqual(expert.absolute_high_watermark, 25000.0)
        
        # Step 3: $26k
        expert.update_daily_watermark(equity=26000.0, balance=25000.0)
        self.assertEqual(expert.absolute_high_watermark, 26000.0)
        
        # Step 4: $25.5k
        expert.update_daily_watermark(equity=25500.0, balance=26000.0)
        self.assertEqual(expert.absolute_high_watermark, 26000.0)
        
        # Step 5: $27k
        expert.update_daily_watermark(equity=27000.0, balance=27000.0)
        self.assertEqual(expert.absolute_high_watermark, 27000.0)
        
        # Step 6: $24k -> Breach (both daily drawdown and trailing floor breached)
        can_trade, msg = expert.can_trade(balance=27000.0, equity=24000.0)
        self.assertFalse(can_trade)
        
        # Isolate trailing floor check specifically
        max_total_allowed = 25000.0 * 0.06
        trailing_floor = expert.absolute_high_watermark - max_total_allowed
        self.assertEqual(trailing_floor, 25500.0)
        self.assertLessEqual(24000.0, trailing_floor)

    def test_consistency_rule_thresholds(self):
        """Cross-validate 35% rule pacing on $25k account."""
        p_targets = [0.0, 400.0, 500.0, 650.0, 750.0, 1500.0]
        # Max single day allowed = $2000 * 0.35 = $700.00
        for p in p_targets:
            res = self.expert_25k.evaluate_consistency_pacing(today_profit=p, total_profit_target=2000.0)
            self.assertEqual(res["max_single_day_allowed"], 700.0)
            if p <= 700.0:
                self.assertTrue(res["is_pacing_safe"])
            else:
                self.assertFalse(res["is_pacing_safe"])

if __name__ == "__main__":
    unittest.main()
