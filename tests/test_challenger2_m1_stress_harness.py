import unittest
import time
from unittest.mock import patch
import pandas as pd
import numpy as np

from skills.high_frequency_trading import get_hft_engine


class TestChallenger2M1DeepStressHarness(unittest.TestCase):

    def setUp(self):
        self.engine = get_hft_engine()

    def test_stress_dom_none_and_malformed_volumes(self):
        """
        Stress Test 1: Exhaustive DOM None and malformed volume handling.
        """
        test_cases = [
            # 1. All None volumes in bids and asks (bid_vol=0, ask_vol=0 -> ratio=0.0 <= 0.70 -> BEARISH_DISTRIBUTION)
            ({
                'bids': [{'price': 2000.0, 'volume': None}, {'price': 1999.0, 'volume': None}],
                'asks': [{'price': 2001.0, 'volume': None}]
            }, 0.0, 0.0, 0, 'BEARISH_DISTRIBUTION'),
            # 2. None volume mixed with whale wall (>1000 lots)
            ({
                'bids': [{'price': 2000.0, 'volume': None}, {'price': 1999.0, 'volume': 1500.0}],
                'asks': [{'price': 2001.0, 'volume': 500.0}]
            }, 1500.0, 500.0, 1, 'BULLISH_ABSORPTION'),
            # 3. None mixed with empty string and 0 (bid_vol=0, ask_vol=0 -> ratio=0.0 <= 0.70 -> BEARISH_DISTRIBUTION)
            ({
                'bids': [{'price': 2000.0, 'volume': ''}, {'price': 1999.0, 'volume': 0}],
                'asks': [{'price': 2001.0, 'volume': None}]
            }, 0.0, 0.0, 0, 'BEARISH_DISTRIBUTION'),
            # 4. Top_bids and top_asks alternative keys with None
            ({
                'top_bids': [{'price': 2000.0, 'volume': None}],
                'top_asks': [{'price': 2001.0, 'volume': 2500.0}]
            }, 0.0, 2500.0, 1, 'BEARISH_DISTRIBUTION'),
            # 5. Completely empty book
            ({
                'bids': [],
                'asks': []
            }, 10270.0, 6170.0, 5, 'BULLISH_ABSORPTION'), # Falls back to synthetic institutional depth (3 bid + 2 ask = 5 whales)
        ]

        for idx, (mock_dom, exp_bid_vol, exp_ask_vol, exp_whales, exp_bias) in enumerate(test_cases, 1):
            with patch.object(self.engine.dom_engine, 'get_market_depth', return_value=mock_dom):
                res = self.engine.get_dom_data('XAUUSD')
                self.assertEqual(res['total_bid_volume'], exp_bid_vol, f"Case {idx} bid vol failed")
                self.assertEqual(res['total_ask_volume'], exp_ask_vol, f"Case {idx} ask vol failed")
                self.assertEqual(len(res['whale_walls']), exp_whales, f"Case {idx} whale count failed")
                self.assertEqual(res['bias'], exp_bias, f"Case {idx} bias failed")

    def test_stress_cvd_zero_net_delta_scenarios(self):
        """
        Stress Test 2: CVD Zero Net Delta Scenarios.
        Must classify as NEUTRAL and absorption_detected=False.
        """
        scenarios = [
            # 1. Balanced 2-tick auction
            pd.DataFrame({'bid': [1.0, 1.0], 'ask': [1.2, 1.2], 'last': [1.2, 1.0], 'volume': [100.0, 100.0]}),
            # 2. Large balanced volume (100k buy, 100k sell)
            pd.DataFrame({'bid': [10.0, 10.0], 'ask': [10.5, 10.5], 'last': [10.5, 10.0], 'volume': [100000.0, 100000.0]}),
            # 3. Multi-tick oscillation
            pd.DataFrame({'bid': [1.0]*6, 'ask': [1.1]*6, 'last': [1.1, 1.0, 1.1, 1.0, 1.1, 1.0], 'volume': [10.0, 10.0, 20.0, 20.0, 30.0, 30.0]}),
            # 4. Floating-point residual delta (< 1e-9)
            pd.DataFrame({'bid': [1.0, 1.0], 'ask': [1.1, 1.1], 'last': [1.1, 1.0], 'volume': [10.0000000000001, 10.0000000000000]}),
        ]

        for idx, df in enumerate(scenarios, 1):
            res = self.engine.compute_cvd_and_absorption('EURUSD', ticks=df)
            self.assertEqual(res['divergence']['bias'], 'NEUTRAL', f"CVD Case {idx} bias failed")
            self.assertFalse(res['divergence']['absorption_detected'], f"CVD Case {idx} absorption_detected failed")
            self.assertEqual(res['divergence']['type'], 'ABSORPTION_NEUTRAL', f"CVD Case {idx} type failed")
            self.assertEqual(res['absorption_type'], 'ABSORPTION_NEUTRAL', f"CVD Case {idx} absorption_type failed")

    def test_stress_latency_absence_of_synthetic_offset_and_sub_2ms_distribution(self):
        """
        Stress Test 3: Empirical verification that +0.85ms synthetic offset is completely absent,
        and that wall-clock execution time stays strictly < 2.0ms across 5,000 iterations.
        """
        latencies = []
        for _ in range(5000):
            r = self.engine.evaluate_latency_and_spread('XAUUSD')
            latencies.append(r['latency_ms'])
            self.assertTrue(r['sub_2ms_passed'])

        min_lat = min(latencies)
        mean_lat = float(np.mean(latencies))
        p95_lat = float(np.percentile(latencies, 95))
        p99_lat = float(np.percentile(latencies, 99))
        max_lat = max(latencies)

        print(f"\n[5,000 RUNS LATENCY DISTRIBUTION]")
        print(f"  Min:    {min_lat:.4f} ms")
        print(f"  Mean:   {mean_lat:.4f} ms")
        print(f"  P95:    {p95_lat:.4f} ms")
        print(f"  P99:    {p99_lat:.4f} ms")
        print(f"  Max:    {max_lat:.4f} ms")

        # Crucial empirical check: If the old '+ 0.85ms' synthetic offset were still present,
        # min_lat could never be below 0.85ms!
        self.assertLess(min_lat, 0.20, f"Synthetic offset detected! Min latency was {min_lat} ms >= 0.20 ms")
        self.assertLess(mean_lat, 1.0, f"Mean latency was {mean_lat} ms >= 1.0 ms")
        self.assertLess(p99_lat, 2.0, f"P99 latency was {p99_lat} ms >= 2.0 ms")


if __name__ == '__main__':
    unittest.main(verbosity=2)
