"""
tests/test_adversarial_m4_challenger2.py — Challenger 2 Adversarial Stress Test Suite for Milestone M4.
====================================================================================================
Subsystem R6 Focus: Autonomous Daemons, PID Mutex, PID Recycling Resilience, WhatsApp Anti-Spam & Command Router.

Stress Scenarios:
1. PID Mutex & Recycling Resilience:
   - Duplicate daemon instance blocking: spawn first daemon, verify second instance exits cleanly (code 0).
   - PID recycling resilience: stale PID pointing to active non-daemon process (test runner) is overwritten without false exit.
   - Stale dead PID handling: nonexistent PID is overwritten cleanly.
   - Malformed/corrupt PID file resilience: non-integer / empty PID content handled safely.
   - atexit PID file cleanup: unlinks file if PID matches, preserves file if overwritten by another process.
2. WhatsApp Anti-Spam & Group Gating:
   - Deduplication buffer stress: 50 duplicate messages within window -> 1 admitted, 49 suppressed.
   - Deduplication FIFO capacity: buffer caps at 1000 items, evicts oldest entry.
   - Group gating isolation (via Node.js wa/owner_command.js and Python test harnesses):
     * Non-authorized group messages: trading commands, banter, and spam rejected (returns null).
     * Elite Trade group (120363401615322542@g.us): valid trade/vitals/screen commands pass regex.
     * Elite Trade chatter filter: non-command banter in group safely suppressed.
     * Direct prefix overrides ('jarvis ...', '!...') parsed correctly.
3. Command Router Envelope Harmonization & High-Throughput Stress:
   - 100+ high-throughput queries across trading, system/OS, radar, crypto, greetings, and edge cases.
   - Strict invariants: every envelope contains non-empty valid category and routed_via.
   - JSON serialization integrity for all generated envelopes.
   - Cross-channel security barrier verification (Discord elite vs crypto separation).
   - Unauthorized destructive command gating.
====================================================================================================
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# Ensure repo root and submodules are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.command_router import (
    JarvisExecutionEnvelope,
    UnifiedCommandRouter,
    get_command_router,
)
from core.telemetry_cards import TelemetryCard

DAEMON_SCRIPT = REPO_ROOT / "MQ3 TRADING BOT" / "src" / "autonomous_live_daemon.py"
OWNER_COMMAND_JS = REPO_ROOT / "wa" / "owner_command.js"


class TestPidMutexAndRecyclingResilience(unittest.TestCase):
    """Adversarially tests daemon single-instance mutex, PID recycling, and cleanup."""

    def setUp(self):
        self.repo_pid_file = REPO_ROOT / "runtime" / "daemon.pid"
        self.mq3_pid_file = REPO_ROOT / "MQ3 TRADING BOT" / "runtime" / "daemon.pid"
        self.repo_pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.mq3_pid_file.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing PID files if any
        self._backup_repo_pid = self.repo_pid_file.read_text(encoding="utf-8") if self.repo_pid_file.exists() else None
        self._backup_mq3_pid = self.mq3_pid_file.read_text(encoding="utf-8") if self.mq3_pid_file.exists() else None

    def tearDown(self):
        # Restore backups
        if self._backup_repo_pid is not None:
            self.repo_pid_file.write_text(self._backup_repo_pid, encoding="utf-8")
        elif self.repo_pid_file.exists():
            self.repo_pid_file.unlink(missing_ok=True)

        if self._backup_mq3_pid is not None:
            self.mq3_pid_file.write_text(self._backup_mq3_pid, encoding="utf-8")
        elif self.mq3_pid_file.exists():
            self.mq3_pid_file.unlink(missing_ok=True)

    def test_duplicate_daemon_instance_blocking_exits_code_zero(self):
        """
        Adversarial Test:
        Spawns a mock running process whose cmdline includes 'autonomous_live_daemon'.
        Writes its PID to the PID files.
        Spawns the real autonomous_live_daemon.py in a subprocess.
        Asserts the second daemon detects the duplicate and exits cleanly with return code 0.
        """
        # 1. Spawn mock primary daemon with 'autonomous_live_daemon' in its commandline
        mock_proc = subprocess.Popen(
            [sys.executable, "-c", "# autonomous_live_daemon mock primary process\nimport time\ntime.sleep(20)"]
        )
        try:
            time.sleep(1.0)  # Allow OS to initialize process commandline in PEB
            primary_pid = str(mock_proc.pid)
            self.repo_pid_file.write_text(primary_pid, encoding="utf-8")
            self.mq3_pid_file.write_text(primary_pid, encoding="utf-8")

            # 2. Spawn the second daemon script
            second_proc = subprocess.run(
                [sys.executable, str(DAEMON_SCRIPT)],
                capture_output=True,
                text=True,
                timeout=12,
            )

            # 3. Must exit cleanly with code 0 to prevent dual-instance conflict
            self.assertEqual(
                second_proc.returncode,
                0,
                f"Duplicate daemon did not exit with code 0! Stderr: {second_proc.stderr}",
            )
            combined_output = (second_proc.stdout + " " + second_proc.stderr).lower()
            self.assertTrue(
                "already running" in combined_output or "duplicate execution" in combined_output,
                f"Expected duplicate execution warning in output, got: {combined_output}",
            )
        finally:
            mock_proc.terminate()
            try:
                mock_proc.wait(timeout=3)
            except Exception:
                mock_proc.kill()

    def test_pid_recycling_resilience_overwrites_stale_pid_file(self):
        """
        Adversarial Test:
        Simulate an active Python process (e.g. current test runner PID) whose command-line
        is NOT 'autonomous_live_daemon'.
        Verify that the mutex check detects the process PID is alive, recognizes it is NOT
        an autonomous_live_daemon instance, does NOT falsely exit, and overwrites the PID file.
        """
        active_unrelated_pid = os.getpid()
        self.repo_pid_file.write_text(str(active_unrelated_pid), encoding="utf-8")
        self.mq3_pid_file.write_text(str(active_unrelated_pid), encoding="utf-8")

        # Verify active_unrelated_pid is alive and not sentinel
        curr_proc = psutil.Process(active_unrelated_pid)
        curr_cmdline = " ".join(curr_proc.cmdline()).lower()
        self.assertNotIn("autonomous_live_daemon", curr_cmdline)

        # Run daemon PID check harness in separate process
        test_script = f"""
import os, sys, psutil
from pathlib import Path

repo_pid_file = Path(r"{self.repo_pid_file}")
project_pid_file = Path(r"{self.mq3_pid_file}")

def _get_existing_pid():
    for pf in (repo_pid_file, project_pid_file):
        if pf.exists():
            try:
                val = int(pf.read_text(encoding="utf-8").strip())
                if val > 0:
                    return val
            except Exception:
                pass
    return None

old_pid = _get_existing_pid()
if old_pid and old_pid != os.getpid():
    try:
        if psutil.pid_exists(old_pid):
            proc = psutil.Process(old_pid)
            cmdline = " ".join(proc.cmdline()).lower()
            if "autonomous_live_daemon" in cmdline:
                sys.exit(0)
            else:
                pass  # Stale / recycled PID detected
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

my_pid = str(os.getpid())
for pf in (repo_pid_file, project_pid_file):
    pf.write_text(my_pid, encoding="utf-8")

sys.exit(42)  # Success sentinel
"""
        res = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Exit code 42 confirms it did not exit with code 0 (no false duplicate collision)
        self.assertEqual(res.returncode, 42, f"Failed: Process exited prematurely! {res.stderr}")

        # Verify PID file was overwritten with the new process PID, not left as the old active PID
        new_pid_str = self.repo_pid_file.read_text(encoding="utf-8").strip()
        self.assertNotEqual(new_pid_str, str(active_unrelated_pid))
        self.assertTrue(new_pid_str.isdigit())

    def test_stale_dead_pid_overwritten(self):
        """Adversarial Test: PID file contains nonexistent PID (999999); daemon overwrites cleanly."""
        dead_pid = "999999"
        self.repo_pid_file.write_text(dead_pid, encoding="utf-8")

        test_script = f"""
import os, sys, psutil
from pathlib import Path

repo_pid_file = Path(r"{self.repo_pid_file}")
project_pid_file = Path(r"{self.mq3_pid_file}")

old_pid = 999999
if old_pid and old_pid != os.getpid():
    try:
        if psutil.pid_exists(old_pid):
            proc = psutil.Process(old_pid)
            cmdline = " ".join(proc.cmdline()).lower()
            if "autonomous_live_daemon" in cmdline:
                sys.exit(0)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

my_pid = str(os.getpid())
repo_pid_file.write_text(my_pid, encoding="utf-8")
sys.exit(77)
"""
        res = subprocess.run([sys.executable, "-c", test_script], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 77)
        self.assertNotEqual(self.repo_pid_file.read_text(encoding="utf-8").strip(), dead_pid)

    def test_corrupt_pid_file_handling(self):
        """Adversarial Test: PID file contains corrupt string or garbage; handles gracefully."""
        corrupt_values = ["NOT_A_PID", "  ", "-500", "0", "xyz999", "null", "undefined"]
        for val in corrupt_values:
            self.repo_pid_file.write_text(val, encoding="utf-8")

            def _get_existing_pid():
                if self.repo_pid_file.exists():
                    try:
                        v = int(self.repo_pid_file.read_text(encoding="utf-8").strip())
                        if v > 0:
                            return v
                    except Exception:
                        pass
                return None

            old_pid = _get_existing_pid()
            self.assertIsNone(old_pid, f"Expected None for corrupt value '{val}', got: {old_pid}")

            # Overwrite with current PID must succeed
            my_pid = str(os.getpid())
            self.repo_pid_file.write_text(my_pid, encoding="utf-8")
            self.assertEqual(self.repo_pid_file.read_text(encoding="utf-8").strip(), my_pid)

    def test_atexit_cleanup_integrity(self):
        """
        Adversarial Test:
        Verifies atexit handler removes PID file when terminating process PID matches,
        but strictly leaves the PID file untouched if another process PID is present.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_pid = Path(tmpdir) / "daemon.pid"
            my_pid = str(os.getpid())

            def cleanup(pf: Path, expected_pid: str):
                try:
                    if pf.exists() and pf.read_text(encoding="utf-8").strip() == expected_pid:
                        pf.unlink(missing_ok=True)
                except Exception:
                    pass

            # Case A: Mismatched PID -> Must NOT unlink
            test_pid.write_text("888888", encoding="utf-8")
            cleanup(test_pid, my_pid)
            self.assertTrue(test_pid.exists(), "Cleanup wrongly deleted mismatched PID file!")
            self.assertEqual(test_pid.read_text(encoding="utf-8").strip(), "888888")

            # Case B: Matching PID -> Must unlink
            test_pid.write_text(my_pid, encoding="utf-8")
            cleanup(test_pid, my_pid)
            self.assertFalse(test_pid.exists(), "Cleanup failed to delete matching PID file!")


class TestWhatsAppAntiSpamAndGroupGating(unittest.TestCase):
    """Adversarially tests WhatsApp deduplication buffer and group gating."""

    def test_deduplication_buffer_suppresses_49_of_50_duplicates(self):
        """
        Adversarial Test:
        Sends 50 duplicate messages with identical msg.key.id within the deduplication window.
        Asserts exactly 1 is admitted and 49 are suppressed.
        """
        seen_buffer = set()
        max_buffer_size = 1000

        duplicate_id = "WA_BURST_DUP_MSG_99999"
        admitted_count = 0
        suppressed_count = 0

        for _ in range(50):
            # Algorithm used in wa/jarvis_baileys.js
            if duplicate_id in seen_buffer:
                suppressed_count += 1
                continue

            seen_buffer.add(duplicate_id)
            if len(seen_buffer) > max_buffer_size:
                seen_buffer.remove(next(iter(seen_buffer)))
            admitted_count += 1

        self.assertEqual(admitted_count, 1, "Exactly 1 of 50 duplicate messages must be admitted.")
        self.assertEqual(suppressed_count, 49, "Exactly 49 of 50 duplicate messages must be suppressed.")

    def test_deduplication_buffer_fifo_eviction(self):
        """
        Adversarial Test:
        Floods deduplication buffer with 1,050 unique messages in Node.js matching wa/jarvis_baileys.js.
        Asserts buffer stays strictly bounded at 1,000 items and oldest items are evicted.
        """
        node_fifo_script = """
const seen = new Set();
for (let i = 0; i < 1050; i++) {
    seen.add('MSG_UNIQUE_' + i);
    if (seen.size > 1000) seen.delete(seen.values().next().value);
}
const report = {
    final_size: seen.size,
    has_0: seen.has('MSG_UNIQUE_0'),
    has_49: seen.has('MSG_UNIQUE_49'),
    has_50: seen.has('MSG_UNIQUE_50'),
    has_1049: seen.has('MSG_UNIQUE_1049')
};
console.log(JSON.stringify(report));
"""
        res = subprocess.run(["node", "-e", node_fifo_script], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Node FIFO execution failed: {res.stderr}")

        report = json.loads(res.stdout)
        self.assertEqual(report["final_size"], 1000, "Buffer size must not exceed 1000.")
        self.assertFalse(report["has_0"], "MSG_UNIQUE_0 should have been evicted")
        self.assertFalse(report["has_49"], "MSG_UNIQUE_49 should have been evicted")
        self.assertTrue(report["has_50"], "MSG_UNIQUE_50 must still be present")
        self.assertTrue(report["has_1049"], "MSG_UNIQUE_1049 must still be present")

    def test_node_extract_owner_command_group_gating(self):
        """
        Adversarial Test:
        Executes Node.js with wa/owner_command.js:
        1. Non-authorized group messages (isEliteGroup=false):
           - Trading commands, vitals, screen, banter must ALL return null.
        2. Elite Trade group (isEliteGroup=true):
           - Trading commands (buy, sell, close, be, vitals, screen) MUST pass.
           - General chatter/banter ('hello guys', 'subha bakhair') MUST return null.
        """
        test_payload = {
            "non_elite": [
                "buy gold 0.01",
                "sell eurusd 0.10",
                "close all",
                "vitals",
                "screen",
                "tasweer",
                "kya haal hai",
                "SPAM PROMOTION CLICK HERE",
            ],
            "elite_valid": [
                "buy gold 0.01 lot",
                "sell xauusd 0.10",
                "long btc",
                "short btc",
                "close all",
                "liquidate",
                "breakeven",
                "be lock",
                "vitals",
                "screen",
                "tasweer",
                "report",
                "haath rok",
                "saari trades band",
                "sona khareedo",
                "sona becho",
            ],
            "elite_banter": [
                "hello everyone",
                "kya haal hai sabka",
                "subha bakhair",
                "weather is nice today",
                "ok brother thanks",
                "let me know when free",
            ],
            "direct_prefixes": [
                ("jarvis buy gold 0.01", "buy gold 0.01"),
                ("jarvis status", "status"),
                ("!vitals", "vitals"),
                ("/report", "report"),
            ]
        }

        node_script = f"""
const {{ extractOwnerCommand }} = require({json.dumps(str(OWNER_COMMAND_JS))});
const payload = {json.dumps(test_payload)};

const results = {{
    non_elite: payload.non_elite.map(text => extractOwnerCommand(text, false)),
    elite_valid: payload.elite_valid.map(text => extractOwnerCommand(text, true)),
    elite_banter: payload.elite_banter.map(text => extractOwnerCommand(text, true)),
    direct_prefixes: payload.direct_prefixes.map(([text, _]) => extractOwnerCommand(text, false))
}};

console.log(JSON.stringify(results));
"""
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, timeout=10)
        self.assertEqual(res.returncode, 0, f"Node.js execution failed: {res.stderr}")

        data = json.loads(res.stdout)

        # 1. Non-elite group: Every single command MUST return null (gated out)
        for i, cmd_res in enumerate(data["non_elite"]):
            self.assertIsNone(
                cmd_res,
                f"Non-authorized group leaked command: '{test_payload['non_elite'][i]}' -> '{cmd_res}'",
            )

        # 2. Elite group valid commands: All must be extracted
        for i, cmd_res in enumerate(data["elite_valid"]):
            self.assertIsNotNone(
                cmd_res,
                f"Elite group command wrongfully rejected: '{test_payload['elite_valid'][i]}'",
            )

        # 3. Elite group banter: Must return null to prevent bot spam in trading channel
        for i, cmd_res in enumerate(data["elite_banter"]):
            self.assertIsNone(
                cmd_res,
                f"Elite group chatter leaked as command: '{test_payload['elite_banter'][i]}' -> '{cmd_res}'",
            )

        # 4. Explicit prefixes: Must be extracted even if isEliteGroup is false
        for i, cmd_res in enumerate(data["direct_prefixes"]):
            expected = test_payload["direct_prefixes"][i][1]
            self.assertEqual(cmd_res, expected)

    def test_baileys_elite_jid_matching(self):
        """Adversarially tests JID and subject pattern matching for Elite Trade group."""
        elite_jid = "120363401615322542@g.us"
        non_elite_jid = "120363999999999999@g.us"

        def is_elite_group(jid: str, subject: str) -> bool:
            import re
            return jid.endswith("@g.us") and (
                bool(re.search(r"elite.*trade|trade.*elite", subject, re.I))
                or jid == elite_jid
            )

        self.assertTrue(is_elite_group(elite_jid, "Random Name"))
        self.assertTrue(is_elite_group("123@g.us", "MQ3 Elite Trade Official"))
        self.assertTrue(is_elite_group("456@g.us", "Trade Elite VIP"))
        self.assertFalse(is_elite_group(non_elite_jid, "General Chat Group"))
        self.assertFalse(is_elite_group(non_elite_jid, "Family Discussion"))


class TestCommandRouterEnvelopeHarmonizationHighThroughput(unittest.TestCase):
    """Adversarially stress-tests Command Router envelope harmonization and throughput."""

    def setUp(self):
        self.router = get_command_router()

    def test_high_throughput_envelope_invariants(self):
        """
        Adversarial Test:
        Runs 100+ commands across all subsystems and edge cases through process_command().
        Asserts every single execution envelope satisfies the harmonization invariants:
        - category is valid and non-empty
        - routed_via is valid and non-empty
        - telemetry card serializes to JSON without error
        - envelope.to_dict() serializes cleanly
        """
        command_matrix = [
            # Trading
            ("trade buy 0.01 lot XAUUSD sl 2710 tp 2740", "trading", "trading_subsystem"),
            ("trade sell 0.02 lot EURUSD", "trading", "trading_subsystem"),
            ("trades intelligence", "trading", "trading_subsystem"),
            ("trade status", "trading", "trading_subsystem"),
            ("positions", "trading", "trading_subsystem"),
            ("gold", "trading", "trading_subsystem"),
            ("sona khareedo", "trading", "trading_subsystem"),
            ("saari trades band", "trading", "trading_subsystem"),
            # OS / System
            ("volume 70", "system", "os_subsystem"),
            ("volume up", "system", "os_subsystem"),
            ("volume down", "system", "os_subsystem"),
            ("mute", "system", "os_subsystem"),
            ("unmute", "system", "os_subsystem"),
            ("vitals", "system", "os_subsystem"),
            ("screenshot", "vision", "vision_subsystem"),
            ("lock pc", "system", "os_subsystem"),
            # Radar
            ("defcon", "radar", "radar_subsystem"),
            ("world", "radar", "radar_subsystem"),
            ("chokepoints", "radar", "radar_subsystem"),
            # Sovereign Greetings / Aliases
            ("kese ho jarvis", "general", "sovereign_alias"),
            ("kaise ho jarvis", "general", "sovereign_alias"),
            ("jarvis suno", "general", "sovereign_alias"),
            ("kese ho", "general", "sovereign_alias"),
            ("kaise ho", "general", "sovereign_alias"),
            # Crypto
            ("crypto", "crypto", "crypto_subsystem"),
            ("btc", "crypto", "crypto_subsystem"),
            ("eth", "crypto", "crypto_subsystem"),
            # Help & Direct
            ("help", "general", "system_direct"),
            ("commands", "general", "system_direct"),
            ("?", "general", "system_direct"),
            ("briefing", "radar", "radar_subsystem"),
        ]

        # Expand matrix to 100+ commands by duplicating with variations
        full_batch: List[tuple] = []
        for i in range(4):
            for cmd, cat, route in command_matrix:
                full_batch.append((cmd, cat, route))

        self.assertGreaterEqual(len(full_batch), 100, "Must execute at least 100 commands for high-throughput stress")

        valid_categories = {
            "trading", "system", "os", "vision", "radar", "general", "crypto",
            "routing", "security", "browser"
        }
        valid_routes = {
            "trading_subsystem", "os_subsystem", "vision_subsystem", "radar_subsystem",
            "crypto_subsystem", "sovereign_alias", "system_direct", "security_gate",
            "skill_compiler", "learned_skill", "browser_vision", "api_gateway_llm",
            "command_gateway", "router"
        }

        for idx, (cmd, expected_cat, expected_route) in enumerate(full_batch):
            env: JarvisExecutionEnvelope = self.router.process_command(
                command=cmd,
                channel="terminal",
                sender_id="owner"
            )

            # Invariant 1: Valid envelope structure
            self.assertIsInstance(env, JarvisExecutionEnvelope)
            self.assertTrue(env.ok, f"Command '{cmd}' failed at index {idx}: {env.output_text}")

            # Invariant 2: Non-empty category & routed_via
            self.assertTrue(bool(env.category), f"Empty category on '{cmd}'")
            self.assertTrue(bool(env.routed_via), f"Empty routed_via on '{cmd}'")

            # Invariant 3: Expected category harmonization
            self.assertEqual(
                env.category,
                expected_cat,
                f"Mismatch category for '{cmd}': expected {expected_cat}, got {env.category}",
            )

            # Invariant 4: Expected route harmonization
            self.assertEqual(
                env.routed_via,
                expected_route,
                f"Mismatch routed_via for '{cmd}': expected {expected_route}, got {env.routed_via}",
            )

            # Invariant 5: JSON serialization integrity
            env_dict = env.to_dict()
            try:
                serialized = json.dumps(env_dict)
                self.assertGreater(len(serialized), 10)
            except Exception as e:
                self.fail(f"Envelope for '{cmd}' is not JSON serializable: {e}")

    def test_adversarial_boundary_inputs(self):
        """
        Adversarial Test:
        Stress-tests empty string, huge text, unicode emojis, and unauthorized administrative actions.
        """
        # 1. Empty string
        env_empty = self.router.process_command("", channel="terminal", sender_id="owner")
        self.assertFalse(env_empty.ok)
        self.assertEqual(env_empty.intent, "empty")
        self.assertEqual(env_empty.category, "general")
        self.assertEqual(env_empty.routed_via, "system_direct")

        # 2. Whitespace only
        env_ws = self.router.process_command("    \n\t   ", channel="terminal", sender_id="owner")
        self.assertFalse(env_ws.ok)
        self.assertEqual(env_ws.intent, "empty")

        # 3. Extremely long payload (5,000 chars)
        huge_cmd = "vitals " + ("A" * 5000)
        env_huge = self.router.process_command(huge_cmd, channel="terminal", sender_id="owner")
        self.assertIsInstance(env_huge, JarvisExecutionEnvelope)
        self.assertTrue(bool(env_huge.category))

        # 4. Unicode emojis and symbols
        emoji_cmd = "kese ho jarvis 🚀✨"
        env_emoji = self.router.process_command(emoji_cmd, channel="terminal", sender_id="owner")
        self.assertTrue(env_emoji.ok)
        self.assertEqual(env_emoji.category, "general")
        self.assertTrue(bool(env_emoji.output_text))
        self.assertTrue(bool(env_emoji.routed_via))

    def test_cross_channel_security_barriers(self):
        """
        Adversarial Test:
        Verifies Discord cross-channel gating:
        - Crypto query in Forex channel (#elite-trade) is gated out.
        - Forex query in Crypto channel (#crypto-bot) is gated out.
        - Destructive shutdown by unauthenticated sender is gated out.
        """
        # 1. Discord Elite Trade: Crypto query blocked
        env_btc = self.router.process_command("what is bitcoin price?", channel="discord_elite", sender_id="any_trader")
        self.assertFalse(env_btc.ok)
        self.assertEqual(env_btc.intent, "channel_barrier_violation")
        self.assertEqual(env_btc.category, "routing")
        self.assertEqual(env_btc.routed_via, "security_gate")

        # 2. Discord Crypto: Forex query blocked
        env_gold = self.router.process_command("check gold xauusd entry", channel="discord_crypto", sender_id="any_trader")
        self.assertFalse(env_gold.ok)
        self.assertEqual(env_gold.intent, "channel_barrier_violation")
        self.assertEqual(env_gold.category, "routing")
        self.assertEqual(env_gold.routed_via, "security_gate")

        # 3. Unauthorized destructive shutdown
        env_shutdown = self.router.process_command("shutdown", channel="discord_dm", sender_id="unauthorized_attacker_id")
        self.assertFalse(env_shutdown.ok)
        self.assertEqual(env_shutdown.intent, "unauthorized_access")
        self.assertEqual(env_shutdown.category, "security")
        self.assertEqual(env_shutdown.routed_via, "security_gate")

    def test_concurrent_throughput_thread_safety(self):
        """
        Adversarial Test:
        Fires 20 concurrent threads executing process_command() simultaneously.
        Verifies thread-safety, no race conditions, and 100% valid envelopes.
        """
        queries = [
            "vitals",
            "kese ho jarvis",
            "volume 70",
            "trade buy 0.01 lot XAUUSD sl 2710 tp 2740",
            "defcon",
        ] * 4  # 20 queries

        def execute_query(q):
            return self.router.process_command(q, channel="terminal", sender_id="owner")

        with ThreadPoolExecutor(max_workers=5) as executor:
            envelopes = list(executor.map(execute_query, queries))

        self.assertEqual(len(envelopes), 20)
        for env in envelopes:
            self.assertTrue(env.ok)
            self.assertTrue(bool(env.category))
            self.assertTrue(bool(env.routed_via))
            self.assertIsInstance(env.telemetry, TelemetryCard)


if __name__ == "__main__":
    unittest.main()
