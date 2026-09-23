import os
import sys
import time
import json
import uuid
import queue
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.rich_terminal_dashboard import RichTerminalDashboard, get_terminal_dashboard_data
from actions.bilingual_parser import parse_bilingual_command
from actions.os_automation import execute_pc_action
from actions.send_discord_intelligence_suite import (
    validate_channel_separation,
    audit_meme_coin_safety,
    CRYPTO_BOT_CHANNEL_ID,
    ELITE_TRADE_CHANNEL_ID,
)
from actions.voice_synthesizer import (
    clean_old_temp_audio_files,
    synthesize_neural_speech,
    SCRATCH_DIR,
)

class TestDeepAdversarial_RomanUrduParser(unittest.TestCase):
    def test_01_colloquial_slang_and_fuzzy_variations(self):
        variations = [
            ('bhai chrome ko band kardo jaldi', 'app_kill', 'Google Chrome', 'ur'),
            ('mt5 ko foran chalao', 'app_launch', 'MetaTrader 5', 'ur'),
            ('thora awaz barha do please', 'system_vol', 'system_volume', 'ur'),
            ('poray repo ka backup banao', 'file_op', 'backup', 'ur'),
            ('vs code khol do samne lao', 'app_launch', 'Visual Studio Code', 'ur'),
            ('system ki sehat kaisi hai batao', 'diagnostics', 'hardware_and_processes', 'ur'),
            ('pc ko furi taur par lock kardo', 'system_power', 'lock', 'ur'),
            ('screen ki tasveer kheecho', 'screen_capture', 'screen', 'ur'),
        ]
        for phrase, exp_action, exp_target, exp_lang in variations:
            res = parse_bilingual_command(phrase)
            self.assertEqual(res.get('action'), exp_action, f'Failed on: {phrase}')
            if exp_target:
                self.assertEqual(res.get('target'), exp_target, f'Target failed on: {phrase}')
            self.assertEqual(res.get('input_lang'), exp_lang, f'Lang failed on: {phrase}')

    def test_02_empty_and_corrupt_command_inputs(self):
        garbage_inputs = [
            '', '   ', '\t\n', '???!!!###', 'None', 'undefined', 'NaN',
            'SELECT * FROM users; --', '<script>alert(1)</script>', 'A' * 500
        ]
        for g in garbage_inputs:
            res = parse_bilingual_command(g)
            self.assertIn('action', res)
            self.assertIn('intent', res)
            self.assertIn('confidence', res)
            self.assertIsInstance(res['confidence'], float)


class TestDeepAdversarial_OSSecurityHarness(unittest.TestCase):
    def test_01_unprivileged_command_injection_and_tampering(self):
        attack_payloads = [
            'Chrome band karo; rm -rf /',
            'shutdown pc && format C:',
            'kill MT5 & calc.exe',
            'pc band karo | echo hacked',
        ]
        for attack in attack_payloads:
            res = execute_pc_action(attack, origin='discord_external', is_owner=False)
            self.assertEqual(res['status'], 'blocked')
            self.assertIn('blocked', res['detail'].lower())
            receipt = res['execution_receipt']
            self.assertEqual(receipt['result']['status'], 'blocked')
            self.assertFalse(receipt['is_owner'])

    def test_02_receipt_hash_and_timing_audit(self):
        for _ in range(20):
            t0 = time.perf_counter()
            res = execute_pc_action('diagnostics', origin='cli', is_owner=True)
            elapsed = (time.perf_counter() - t0) * 1000
            self.assertIn(res['status'], ('success', 'error'))
            rcpt = res['execution_receipt']
            self.assertTrue(rcpt['receipt_id'].startswith('rcpt_'))
            self.assertLess(rcpt['execution_time_ms'], 1500.0)


class TestDeepAdversarial_HighVelocityUIQueue(unittest.TestCase):
    def test_01_massive_concurrency_no_drops_or_race_conditions(self):
        dash = RichTerminalDashboard()
        in_q = queue.Queue()
        out_list = []
        stop = threading.Event()
        N = 200

        def _prod(tid):
            for i in range(N // 4):
                in_q.put(f'help --tid={tid}-{i}')

        def _cons():
            while not stop.is_set() or not in_q.empty():
                try:
                    c = in_q.get(timeout=0.02)
                    r = dash.execute_command(c)
                    out_list.append(r)
                    in_q.task_done()
                except queue.Empty:
                    pass

        with patch('ai_engine.query_ai', return_value='AI Mock'):
            t_cons = threading.Thread(target=_cons, daemon=True)
            t_cons.start()

            prods = [threading.Thread(target=_prod, args=(t,), daemon=True) for t in range(4)]
            for p in prods:
                p.start()
            for p in prods:
                p.join(timeout=5.0)

            in_q.join()
            stop.set()
            t_cons.join(timeout=5.0)

            self.assertEqual(len(out_list), N)


class TestDeepAdversarial_DiscordMemeHoneypot(unittest.TestCase):
    def test_01_malicious_tax_and_honeypot_combinations(self):
        # 1. Low LP lock + 99% tax -> fails with score 50 and High Tax flag
        res1 = audit_meme_coin_safety({
            'symbol': 'SUPER_SCAM',
            'lp_locked_pct': 70.0,
            'contract_renounced': True,
            'mint_authority_disabled': True,
            'buy_tax_pct': 99.0,
            'sell_tax_pct': 99.0,
            'top_10_holders_pct': 5.0,
            'honeypot_safe': True
        })
        self.assertFalse(res1['passed'])
        self.assertIn('High Tax', ' '.join(res1['risk_flags']))

        # 2. 98% dev hold + low LP lock -> fails
        res2 = audit_meme_coin_safety({
            'symbol': 'WHALE_SCAM',
            'lp_locked_pct': 80.0,
            'contract_renounced': True,
            'mint_authority_disabled': True,
            'buy_tax_pct': 0.0,
            'sell_tax_pct': 0.0,
            'top_10_holders_pct': 98.0,
            'honeypot_safe': True
        })
        self.assertFalse(res2['passed'])
        self.assertEqual(res2['safety_score'], 50.0)
        self.assertIn('High Dev/Whale Concentration', ' '.join(res2['risk_flags']))

        # 3. Honeypot fail override
        res3 = audit_meme_coin_safety({
            'symbol': 'HIDDEN_HONEYPOT',
            'lp_locked_pct': 100.0,
            'contract_renounced': True,
            'mint_authority_disabled': True,
            'buy_tax_pct': 0.0,
            'sell_tax_pct': 0.0,
            'top_10_holders_pct': 5.0,
            'honeypot_safe': False
        })
        self.assertEqual(res3['safety_score'], 0.0)
        self.assertFalse(res3['passed'])


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    sys.exit(0 if res.wasSuccessful() else 1)
