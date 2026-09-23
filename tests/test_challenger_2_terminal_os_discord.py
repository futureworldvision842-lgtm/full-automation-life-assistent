import os
import sys
import time
import json
import uuid
import queue
import socket
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.rich_terminal_dashboard import (
    RichTerminalDashboard,
    get_terminal_dashboard_data,
    render_terminal_dashboard,
    _check_port_socket,
)
from actions.bilingual_parser import (
    BilingualParser,
    bilingual_parser,
    parse_bilingual_command,
    APP_ALIASES_MAP,
)
from actions.os_automation import (
    execute_pc_action,
    inspect_apps,
    terminate_app,
    launch_app,
    switch_app,
)
from actions.send_discord_intelligence_suite import (
    CRYPTO_BOT_CHANNEL_ID,
    ELITE_TRADE_CHANNEL_ID,
    validate_channel_separation,
    audit_meme_coin_safety,
    generate_crypto_intelligence_payload,
    generate_forex_intelligence_payload,
    generate_portfolio_telemetry_payload,
    send_discord_embed_with_response,
)
from actions.voice_synthesizer import (
    clean_old_temp_audio_files,
    synthesize_neural_speech,
    get_available_voices,
    SCRATCH_DIR,
)

class TestChallenger2_TerminalVisualizer(unittest.TestCase):
    def setUp(self):
        self.dashboard = RichTerminalDashboard()

    def test_01_non_blocking_async_queue_rapid_typing_burst(self):
        input_queue = queue.Queue()
        processed_commands = []
        stop_event = threading.Event()
        commands_to_send = [
            'trade', 'trade gold', 'vitals', 'status', 'defcon',
            'chokepoints', 'open chrome', 'kya haal hai', 'help',
            'sona ka rate', 'open mt5', 'pc vitals', 'pnl'
        ]
        total_commands = 600

        with patch('subprocess.Popen'), \
             patch('requests.get', side_effect=ConnectionRefusedError('Fast test mock')), \
             patch('actions.mq3_trading.mq3_trading', return_value='MQ3 OK'), \
             patch('actions.world_monitor.world_monitor', return_value='WORLD OK'), \
             patch('ai_engine.query_ai', return_value='AI OK'):
            def _producer(thread_id: int):
                for i in range(total_commands // 4):
                    cmd = commands_to_send[(thread_id + i) % len(commands_to_send)]
                    input_queue.put(f'{cmd} --thread={thread_id} --seq={i}')
                    time.sleep(0.0001)

            def _consumer():
                while not stop_event.is_set() or not input_queue.empty():
                    try:
                        cmd = input_queue.get(timeout=0.05)
                        res = self.dashboard.execute_command(cmd)
                        processed_commands.append((cmd, res))
                        input_queue.task_done()
                    except queue.Empty:
                        pass

            start_time = time.perf_counter()
            consumer_thread = threading.Thread(target=_consumer, daemon=True)
            consumer_thread.start()

            producers = [threading.Thread(target=_producer, args=(t,), daemon=True) for t in range(4)]
            for p in producers:
                p.start()
            for p in producers:
                p.join(timeout=5.0)

            input_queue.join()
            stop_event.set()
            consumer_thread.join(timeout=5.0)
            elapsed_sec = time.perf_counter() - start_time

            self.assertEqual(len(processed_commands), total_commands)
            self.assertLess(elapsed_sec, 6.0)
            self.assertTrue(len(self.dashboard.command_history) > 0)

    def test_02_100_percent_offline_fallback_when_services_down(self):
        with patch('requests.get', side_effect=ConnectionRefusedError('Target port offline / unreachable')), \
             patch('socket.socket.connect_ex', return_value=111):
            data = get_terminal_dashboard_data()
            self.assertIn('trading', data)
            self.assertIn('defcon', data)
            self.assertIn('fleet_vitals', data)
            self.assertIn('system_vitals', data)

            trading = data['trading']
            self.assertEqual(trading['login'], 1514382598)
            self.assertEqual(trading['server'], 'FTMO-Demo')
            self.assertGreaterEqual(trading['balance'], 1000.0)
            self.assertIsInstance(trading['open_positions'], list)

            defcon = data['defcon']
            self.assertEqual(defcon['threat_level'], 'DEFCON 2')
            self.assertEqual(len(defcon['maritime_chokepoints']), 5)
            self.assertEqual(defcon['gold_multiplier'], 1.45)
            self.assertEqual(defcon['sentiment'], 'BEARISH_RISK_OFF')

            fleet = data['fleet_vitals']
            self.assertFalse(fleet['dashboard'])
            self.assertFalse(fleet['mobile'])
            self.assertFalse(fleet['mq3'])
            self.assertFalse(fleet['odysseus'])
            self.assertFalse(fleet['ollama'])
            self.assertFalse(fleet['world_monitor'])

            layout = self.dashboard.build_layout(data)
            self.assertIsNotNone(layout)
            self.assertEqual(layout['header'].name, 'header')
            self.assertEqual(layout['trading'].name, 'trading')
            self.assertEqual(layout['defcon'].name, 'defcon')
            self.assertEqual(layout['fleet'].name, 'fleet')
            self.assertEqual(layout['system'].name, 'system')

    def test_03_data_schema_stability_all_4_panels_extreme_inputs(self):
        extreme_payloads = [
            {
                'trading': {'login': 5054542, 'server': 'Vebson-Server', 'balance': 920.50, 'equity': 850.00, 'open_positions': [{'symbol': 'XAUUSD', 'profit': -70.50}], 'floating_pnl': -70.50, 'win_rate': 45.2},
                'defcon': {'threat_level': 'DEFCON 1', 'maritime_chokepoints': [{'name': 'Hormuz', 'status': 'BLOCKED', 'threat_score': 99, 'flow': '0 bpd'}], 'gold_multiplier': 2.50, 'sentiment': 'CRITICAL_PANIC'},
                'fleet_vitals': {'dashboard': True, 'mobile': False, 'mq3': True, 'odysseus': False, 'ollama': False, 'world_monitor': True, 'discord_bot': True},
                'system_vitals': {'cpu_pct': 99.9, 'ram_pct': 98.5, 'gpu_pct': 100.0, 'network_latency_ms': 450.2}
            },
            {
                'trading': {'login': 0, 'server': 'UNKNOWN', 'balance': 0.0, 'equity': 0.0, 'open_positions': [], 'floating_pnl': 0.0, 'win_rate': 0.0},
                'defcon': {'threat_level': 'DEFCON 5', 'maritime_chokepoints': [], 'gold_multiplier': 1.0, 'sentiment': 'NEUTRAL'},
                'fleet_vitals': {'dashboard': False, 'mobile': False, 'mq3': False, 'odysseus': False, 'ollama': False, 'world_monitor': False, 'discord_bot': False},
                'system_vitals': {'cpu_pct': 0.0, 'ram_pct': 0.0, 'gpu_pct': 0.0, 'network_latency_ms': 0.1}
            }
        ]
        for p in extreme_payloads:
            layout = self.dashboard.build_layout(p)
            self.assertIsNotNone(layout)
            p_trade = self.dashboard.create_trading_panel(p)
            self.assertIsNotNone(p_trade)
            p_defcon = self.dashboard.create_defcon_panel(p)
            self.assertIsNotNone(p_defcon)
            p_fleet = self.dashboard.create_fleet_panel(p)
            self.assertIsNotNone(p_fleet)
            p_sys = self.dashboard.create_system_vitals_panel(p)
            self.assertIsNotNone(p_sys)

class TestChallenger2_OSSovereignComputerControl(unittest.TestCase):
    def test_01_bilingual_roman_urdu_and_english_parsing(self):
        test_cases = [
            ('Chrome band karo', 'app_kill', 'Google Chrome', 'ur'),
            ('MT5 chalao', 'app_launch', 'MetaTrader 5', 'ur'),
            ('volume barhao', 'system_vol', 'system_volume', 'ur'),
            ('repo backup banao', 'file_op', 'backup', 'ur'),
            ('close chrome', 'app_kill', 'Google Chrome', 'en'),
            ('launch mt5', 'app_launch', 'MetaTrader 5', 'en'),
            ('increase volume', 'system_vol', 'system_volume', 'en'),
            ('backup workspace', 'file_op', 'backup', 'en'),
            ('VS Code kholo', 'app_launch', 'Visual Studio Code', 'ur'),
            ('Discord band kar do', 'app_kill', 'Discord', 'ur'),
            ('awaz kam karo', 'system_vol', 'system_volume', 'ur'),
            ('system ki sehat check karo', 'diagnostics', 'hardware_and_processes', 'ur'),
            ('pc lock karo', 'system_power', 'lock', 'ur'),
            ('lock pc', 'system_power', 'lock', 'en'),
            ('screenshot lo', 'screen_capture', 'screen', 'ur'),
            ('take screenshot', 'screen_capture', 'screen', 'en'),
        ]
        for cmd, expected_action, expected_target, expected_lang in test_cases:
            parsed = parse_bilingual_command(cmd)
            self.assertEqual(parsed.get('action'), expected_action, f'Command {cmd} failed action match')
            if expected_target:
                self.assertEqual(parsed.get('target'), expected_target, f'Command {cmd} failed target match')
            self.assertEqual(parsed.get('input_lang'), expected_lang, f'Command {cmd} failed language detection')
            self.assertGreaterEqual(parsed.get('confidence', 0.0), 0.80)

    def test_02_execution_receipts_structure_and_latency(self):
        commands = [
            'diagnostics',
            'list running apps',
            'volume 50%',
            'search file main.py',
            'screenshot lo'
        ]
        for cmd in commands:
            res = execute_pc_action(cmd, origin='cli', is_owner=True)
            self.assertIn('status', res)
            self.assertIn('action', res)
            self.assertIn('detail', res)
            self.assertIn('stdout_summary', res)
            self.assertIn('bilingual_translation', res)
            self.assertIn('execution_receipt', res)

            receipt = res['execution_receipt']
            self.assertTrue(receipt['receipt_id'].startswith('rcpt_'))
            self.assertEqual(len(receipt['receipt_id']), 17)
            self.assertIn('timestamp', receipt)
            self.assertEqual(receipt['origin'], 'cli')
            self.assertTrue(receipt['is_owner'])
            max_lat = 5000.0 if cmd in ('diagnostics', 'search file main.py', 'list running apps') else 1500.0
            lat_val = receipt['execution_time_ms']
            self.assertLess(lat_val, max_lat, f"Command {cmd} latency exceeded limit: {lat_val}ms")
            self.assertIn('result', receipt)

    def test_03_security_authorization_blocks_unprivileged_calls(self):
        privileged_commands = [
            'Chrome band karo',
            'kill MT5',
            'shutdown pc',
            'restart computer',
            'pc band karo'
        ]
        for cmd in privileged_commands:
            res = execute_pc_action(cmd, origin='discord_guest', is_owner=False)
            self.assertEqual(res['status'], 'blocked')
            self.assertIn('blocked', res['detail'].lower())
            self.assertIn('SECURITY BLOCKED', res['stdout_summary'])

            receipt = res['execution_receipt']
            self.assertFalse(receipt['is_owner'])
            self.assertEqual(receipt['result']['status'], 'blocked')
            self.assertEqual(receipt['result']['reason'], 'unauthorized_origin')

        unprivileged_res = execute_pc_action('diagnostics', origin='guest', is_owner=False)
        self.assertIn(unprivileged_res['status'], ('success', 'error'))
        self.assertNotEqual(unprivileged_res['status'], 'blocked')

class TestChallenger2_DiscordDualChannelAndVoice(unittest.TestCase):
    def test_01_zero_percent_cross_channel_leakage(self):
        self.assertTrue(validate_channel_separation(CRYPTO_BOT_CHANNEL_ID, 'crypto'))
        self.assertFalse(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, 'crypto'))
        self.assertTrue(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, 'forex'))
        self.assertTrue(validate_channel_separation(ELITE_TRADE_CHANNEL_ID, 'prop'))
        self.assertFalse(validate_channel_separation(CRYPTO_BOT_CHANNEL_ID, 'forex'))
        self.assertFalse(validate_channel_separation(CRYPTO_BOT_CHANNEL_ID, 'prop'))

        leak_count = 0
        for i in range(500):
            c_type = 'crypto' if i % 2 == 0 else 'forex'
            target_chan = CRYPTO_BOT_CHANNEL_ID if i % 3 == 0 else ELITE_TRADE_CHANNEL_ID
            is_valid = validate_channel_separation(target_chan, c_type)
            if c_type == 'crypto' and target_chan == ELITE_TRADE_CHANNEL_ID and is_valid:
                leak_count += 1
            if c_type == 'forex' and target_chan == CRYPTO_BOT_CHANNEL_ID and is_valid:
                leak_count += 1
        self.assertEqual(leak_count, 0)

        with patch('actions.send_discord_intelligence_suite.fetch_crypto_live_data', return_value={
            'bitcoin': {'usd': 88450.0, 'usd_24h_change': 3.45},
            'ethereum': {'usd': 2840.5, 'usd_24h_change': 2.80},
            'solana': {'usd': 142.60, 'usd_24h_change': 6.25},
            'sui': {'usd': 2.85}, 'bittensor': {'usd': 540.0},
            'ondo-finance': {'usd': 1.05}, 'pepe': {'usd': 0.00001045},
            'bonk': {'usd': 0.00002450}, 'dogwifcoin': {'usd': 2.65}
        }), patch('actions.send_discord_intelligence_suite.fetch_mt5_forex_data', return_value={
            'XAUUSD': {'bid': 4652.40, 'ask': 4652.85, 'spread': 0.45},
            'EURUSD': {'bid': 1.16850, 'ask': 1.16865, 'spread': 0.00015},
            'GBPUSD': {'bid': 1.36540, 'ask': 1.36558, 'spread': 0.00018},
            'USDJPY': {'bid': 158.820, 'ask': 158.865, 'spread': 0.045}
        }):
            crypto_payload = generate_crypto_intelligence_payload()
            self.assertIn('#crypto-bot', crypto_payload['footer']['text'])
            self.assertIn('CRYPTO RESEARCH', crypto_payload['title'])

            forex_payload = generate_forex_intelligence_payload()
            self.assertIn('#elite-trade', forex_payload['footer']['text'])
            self.assertIn('INSTITUTIONAL FOREX', forex_payload['title'])

            portfolio_payload = generate_portfolio_telemetry_payload()
            self.assertIn('Prop Risk Core', portfolio_payload['footer']['text'])

    def test_02_on_chain_meme_coin_honeypot_detection(self):
        safe_token = {
            'symbol': 'SAFE_PEPE',
            'lp_locked_pct': 100.0,
            'contract_renounced': True,
            'mint_authority_disabled': True,
            'buy_tax_pct': 0.0,
            'sell_tax_pct': 0.0,
            'top_10_holders_pct': 10.5,
            'honeypot_safe': True
        }
        res_safe = audit_meme_coin_safety(safe_token)
        self.assertTrue(res_safe['passed'])
        self.assertEqual(res_safe['safety_score'], 100.0)
        self.assertIn('VERIFIED SAFE', res_safe['verdict'])

        honeypot_token = {
            'symbol': 'HONEY_SCAM',
            'lp_locked_pct': 100.0,
            'contract_renounced': True,
            'mint_authority_disabled': True,
            'buy_tax_pct': 0.0,
            'sell_tax_pct': 0.0,
            'top_10_holders_pct': 10.0,
            'honeypot_safe': False
        }
        res_honey = audit_meme_coin_safety(honeypot_token)
        self.assertFalse(res_honey['passed'])
        self.assertEqual(res_honey['safety_score'], 0.0)
        self.assertIn('HIGH RISK', res_honey['verdict'])
        self.assertTrue(any('HONEYPOT' in flag for flag in res_honey['risk_flags']))

        toxic_token = {
            'symbol': 'RUG_TOKEN',
            'lp_locked_pct': 30.0,
            'contract_renounced': False,
            'mint_authority_disabled': False,
            'buy_tax_pct': 15.0,
            'sell_tax_pct': 25.0,
            'top_10_holders_pct': 65.0,
            'honeypot_safe': True
        }
        res_toxic = audit_meme_coin_safety(toxic_token)
        self.assertFalse(res_toxic['passed'])
        self.assertEqual(res_toxic['safety_score'], 5.0)
        self.assertEqual(len(res_toxic['risk_flags']), 4)

    def test_03_voice_synthesis_temp_file_cleanup(self):
        now = time.time()
        old_file_1 = SCRATCH_DIR / 'jarvis_voice_test_old_1.mp3'
        old_file_2 = SCRATCH_DIR / 'jarvis_voice_test_old_2.wav'
        old_file_1.write_text('mock old audio 1', encoding='utf-8')
        old_file_2.write_text('mock old audio 2', encoding='utf-8')
        os.utime(old_file_1, (now - 5000, now - 5000))
        os.utime(old_file_2, (now - 4500, now - 4500))

        fresh_file = SCRATCH_DIR / 'jarvis_voice_test_fresh.mp3'
        fresh_file.write_text('mock fresh audio', encoding='utf-8')
        os.utime(fresh_file, (now - 10, now - 10))

        keep_file = SCRATCH_DIR / 'do_not_delete.txt'
        keep_file.write_text('important persistent state', encoding='utf-8')
        os.utime(keep_file, (now - 10000, now - 10000))

        try:
            removed = clean_old_temp_audio_files(max_age_seconds=3600)
            self.assertGreaterEqual(removed, 2)
            self.assertFalse(old_file_1.exists())
            self.assertFalse(old_file_2.exists())
            self.assertTrue(fresh_file.exists())
            self.assertTrue(keep_file.exists())
        finally:
            fresh_file.unlink(missing_ok=True)
            keep_file.unlink(missing_ok=True)

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
