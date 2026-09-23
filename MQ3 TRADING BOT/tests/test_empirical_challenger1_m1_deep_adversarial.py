"""
tests/test_empirical_challenger1_m1_deep_adversarial.py — Empirical Challenger Deep Adversarial Test Suite for M1.
===================================================================================================================
Adversarially probes:
1. Purged numbers (923487117832, 923322555238, 923375893095) with comprehensive mutation matrix:
   - raw, +92, 0092, 03xx, spaces, dashes, null-bytes, control chars, domain spoofing, device suffixes.
2. Group prefix spoofing probes exposing substring/prefix vulnerabilities in group whitelist checks.
3. Master Owner 923468053268 in all valid JID, device, and LID formats.
4. Master Owner negative spoofing (prefix/suffix padding, domain tampering, null byte injections).
5. Elite Trade Group 120363401615322542@g.us exact matching vs unapproved group JIDs.
6. Silent drop & zero disclosure verification across all command categories via WhatsAppQRManager & Web Terminal API.
7. Execution speed / latency SLA (sub-500ms response for owner, instant sub-5ms silent drop for attackers).
8. Broadcast routines (CommunitySignalBroadcaster and DailyInstitutionalRoutineEngine) recipient isolation.
9. Entire codebase zero-leakage scan for secondary family numbers in src/ and config.json.
"""

import os
import sys
import re
import json
import time
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.whatsapp_qr_manager import (
    is_whitelisted_number,
    WhatsAppQRManager,
    AUTHORIZED_CONTACTS,
    ALLOWED_SET,
    ELITE_TRADE_GROUP_JID
)
from src.web_terminal_server import app, terminal_state
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine


PURGED_NUMBERS = ["923487117832", "923322555238", "923375893095"]
MASTER_OWNER = "923468053268"
ELITE_GROUP = "120363401615322542@g.us"


# =====================================================================
# 1. Purged Numbers Adversarial Mutation Matrix
# =====================================================================

class TestPurgedNumbersMutationMatrix:
    """Stress tests every purged contact across exhaustive permutations to ensure absolute rejection."""

    @pytest.mark.parametrize("num", PURGED_NUMBERS)
    def test_purged_number_raw_formats(self, num):
        local = "0" + num[2:]
        intl_00 = "00" + num
        plus_num = "+" + num
        with_spaces = f"+{num[:2]} {num[2:5]} {num[5:]}"
        with_dashes = f"+{num[:2]}-{num[2:5]}-{num[5:]}"

        variations = [
            num,
            local,
            intl_00,
            plus_num,
            with_spaces,
            with_dashes,
            f" {num} ",
            f"\t{num}\n"
        ]
        for v in variations:
            assert is_whitelisted_number(v) is False, f"Purged number variation allowed: {repr(v)}"

    @pytest.mark.parametrize("num", PURGED_NUMBERS)
    def test_purged_number_jid_formats(self, num):
        variations = [
            f"{num}@s.whatsapp.net",
            f"+{num}@s.whatsapp.net",
            f"00{num}@s.whatsapp.net",
            f"0{num[2:]}@s.whatsapp.net",
            f"{num}:0@s.whatsapp.net",
            f"{num}:1@s.whatsapp.net",
            f"{num}:99@s.whatsapp.net",
            f"{num}@g.us",
            f"{num}@c.us",
            f"{num}@broadcast"
        ]
        for v in variations:
            assert is_whitelisted_number(v) is False, f"Purged JID variation allowed: {repr(v)}"

    @pytest.mark.parametrize("num", PURGED_NUMBERS)
    def test_purged_number_injection_payloads(self, num):
        payloads = [
            f"{num}\x00@s.whatsapp.net",
            f"{num}\r\n@s.whatsapp.net",
            f"{num}\x1b[31m@s.whatsapp.net",
            f"{num}\x7f@s.whatsapp.net",
            f"{num}; DROP TABLE users;--",
            f"{num}' OR '1'='1",
            f"{num}../etc/passwd",
            f"{{'{num}': True}}"
        ]
        for p in payloads:
            assert is_whitelisted_number(p) is False, f"Purged injection payload allowed: {repr(p)}"


# =====================================================================
# 2. Master Owner Whitelist & LID Matrix
# =====================================================================

class TestMasterOwnerWhitelistInvariants:
    """Verifies that legitimate Master Owner formats are accepted reliably."""

    def test_master_owner_valid_permutations(self):
        valid_cases = [
            "923468053268",
            "+923468053268",
            "03468053268",
            "00923468053268",
            "+92 346 8053268",
            "+92-346-8053268",
            "923468053268@s.whatsapp.net",
            "+923468053268@s.whatsapp.net",
            "03468053268@s.whatsapp.net",
            "00923468053268@s.whatsapp.net",
            "923468053268:0@s.whatsapp.net",
            "923468053268:1@s.whatsapp.net",
            "923468053268:12@s.whatsapp.net",
            "923468053268@lid",
            "linked_device_user@lid"
        ]
        for c in valid_cases:
            assert is_whitelisted_number(c) is True, f"Legitimate Master Owner format rejected: {repr(c)}"

    def test_master_owner_negative_spoofs(self):
        spoofs = [
            "9234680532680",             # extra digit at end
            "1923468053268",             # extra digit at start
            "92346805326",               # missing digit
            "923468053268@evil.com",     # wrong domain
            "923468053268@c.us",         # unapproved domain
            "923468053268@s.whatsapp.net.evil.com", # domain evasion
            "923468053268:abc@s.whatsapp.net",     # invalid device port
            "923468053268\x00@s.whatsapp.net",     # null byte
            "923468053268\r\n@s.whatsapp.net",    # CRLF
            "923468053268\x1f@s.whatsapp.net",     # control char
            "923468053268\x7f@s.whatsapp.net",     # DEL char
            "status@broadcast",                    # broadcast spoof
            "923468053268@broadcast"               # broadcast spoof
        ]
        for s in spoofs:
            assert is_whitelisted_number(s) is False, f"Master Owner spoof mistakenly allowed: {repr(s)}"


# =====================================================================
# 3. Elite Trade Group & Unapproved Group JIDs
# =====================================================================

class TestGroupSecurityInvariants:
    """Verifies Elite Trade Group admission and unapproved group silent rejection."""

    def test_elite_trade_group_accepted(self):
        cases = [
            "120363401615322542@g.us",
            "120363401615322542",
            "120363401615322542@g.us "
        ]
        for c in cases:
            assert is_whitelisted_number(c) is True, f"Elite Trade Group rejected: {repr(c)}"

    def test_unapproved_groups_rejected(self):
        unapproved = [
            "120363401615322543@g.us",  # off by 1
            "12036340161532254@g.us",   # truncated
            "199999999999999999@g.us",  # random group
            "family_group@g.us",
            "crypto_signals@g.us",
            "120363401615322542\x00@g.us",
            "120363401615322542\n@g.us"
        ]
        for g in unapproved:
            assert is_whitelisted_number(g) is False, f"Unapproved group allowed: {repr(g)}"


# =====================================================================
# 4. Silent Drop & Zero Information Leakage via Handler
# =====================================================================

class TestSilentDropAndZeroDisclosure:
    """Verifies that all commands from unauthorized senders yield empty string and no error info."""

    COMMANDS_TO_TEST = [
        "status",
        "balance",
        "equity",
        "fleet",
        "trades",
        "gold",
        "evidence",
        "plan",
        "why",
        "scan",
        "signal",
        "news",
        "whale",
        "world",
        "crisis",
        "crypto",
        "gsr",
        "brain",
        "advisor",
        "vision",
        "morning",
        "night",
        "buy gold 0.10",
        "sell btc 0.5",
        "breakeven",
        "kill switch",
        "pause",
        "resume"
    ]

    @pytest.mark.parametrize("cmd", COMMANDS_TO_TEST)
    def test_unauthorized_commands_return_empty_string(self, cmd):
        mgr = WhatsAppQRManager()
        unauthorized_senders = [
            "923487117832",
            "923322555238",
            "923375893095",
            "+12025550199",
            "attacker@s.whatsapp.net",
            "120363999999999999@g.us",
            "",
            None,
            "923468053268\x00extra"
        ]
        for sender in unauthorized_senders:
            try:
                res = mgr.handle_incoming_command(cmd, sender)
                assert res == "", f"Information leakage: cmd '{cmd}' from '{sender}' returned: {repr(res)}"
            except Exception as e:
                pytest.fail(f"Exception raised on unauthorized sender '{sender}' with cmd '{cmd}': {e}")

    def test_authorized_master_owner_receives_replies(self):
        mgr = WhatsAppQRManager()
        res = mgr.handle_incoming_command("status", "923468053268")
        assert isinstance(res, str)
        assert len(res) > 0, "Authorized Master Owner received empty response for 'status'"
        assert ("Account" in res or "Balance" in res or "TELEMETRY" in res or "Equity" in res), (
            f"Unexpected status response: {res}"
        )


# =====================================================================
# 5. Web Terminal REST API Verification
# =====================================================================

class TestWebTerminalAPIContract:
    """Verifies REST endpoints /api/whatsapp_qr and /api/whatsapp_command."""

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def test_whatsapp_qr_endpoint_contract(self):
        res = self.client.get("/api/whatsapp_qr")
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") == "success"
        assert data.get("authorized_contacts") == ["923468053268"]
        assert data.get("elite_group") == "120363401615322542@g.us"
        for purged in PURGED_NUMBERS:
            assert purged not in data.get("authorized_contacts")

    def test_whatsapp_command_endpoint_unauthorized_drop(self):
        for purged in PURGED_NUMBERS:
            payload = {"command": "status", "sender": purged}
            res = self.client.post("/api/whatsapp_command", json=payload)
            assert res.status_code == 403

    def test_whatsapp_command_endpoint_authorized_success(self):
        payload = {"command": "status", "sender": "923468053268"}
        res = self.client.post("/api/whatsapp_command", json=payload)
        assert res.status_code == 200
        assert len(res.json()["response"]) > 0


# =====================================================================
# 6. Broadcast Modules Recipient Isolation
# =====================================================================

class TestBroadcastRecipientIsolation:
    """Verifies that CommunitySignalBroadcaster and DailyInstitutionalRoutineEngine isolate recipients."""

    def test_community_signal_broadcaster_recipients(self):
        broadcaster = CommunitySignalBroadcaster()
        with patch.object(broadcaster.qr_manager, "send_message", return_value=True) as mock_send:
            res = broadcaster.broadcast_signal("Test Signal")
            assert len(res) == 1
            assert "Master User (Owner) (923468053268)" in res
            mock_send.assert_called_once_with("Test Signal", to="923468053268")

    def test_daily_routine_engine_recipients(self):
        routine_engine = DailyInstitutionalRoutineEngine()
        with patch.object(routine_engine.qr_manager, "send_message", return_value=True) as mock_send:
            res = routine_engine.broadcaster.broadcast_signal("Test Morning Briefing")
            assert len(res) == 1
            assert "Master User (Owner) (923468053268)" in res
            mock_send.assert_called_once_with("Test Morning Briefing", to="923468053268")


# =====================================================================
# 7. Codebase Static Purge Verification
# =====================================================================

class TestCodebasePurgeIntegrity:
    """Scans config.json and all Python source files to ensure zero instances of purged numbers."""

    def test_config_json_purged_contacts(self):
        config_path = os.path.join(PROJECT_ROOT, "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        auth_contacts = cfg.get("whatsapp", {}).get("authorized_contacts", [])
        phones = [c.get("phone") for c in auth_contacts]
        assert phones == ["923468053268"], f"config.json authorized_contacts mismatch: {phones}"
        for p in PURGED_NUMBERS:
            assert p not in phones

    def test_src_directory_contains_zero_purged_numbers(self):
        src_dir = os.path.join(PROJECT_ROOT, "src")
        found = []
        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        for p in PURGED_NUMBERS:
                            if p in content:
                                found.append((file, p))
        assert found == [], f"Purged numbers found in src/ files: {found}"


# =====================================================================
# 8. Performance SLA Verification (Sub-500ms response & Sub-5ms drop)
# =====================================================================

class TestPerformanceSLA:
    """Verifies sub-500ms response time for Master Owner and instant drop for unauthorized senders."""

    def test_unauthorized_drop_latency_under_5ms(self):
        mgr = WhatsAppQRManager()
        for p in PURGED_NUMBERS:
            t0 = time.perf_counter()
            res = mgr.handle_incoming_command("status", p)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert res == ""
            assert elapsed_ms < 5.0, f"Unauthorized drop took too long: {elapsed_ms:.2f}ms"

    def test_authorized_command_latency_under_500ms(self):
        mgr = WhatsAppQRManager()
        t0 = time.perf_counter()
        res = mgr.handle_incoming_command("status", "923468053268")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert len(res) > 0
        assert elapsed_ms < 500.0, f"Authorized command took too long: {elapsed_ms:.2f}ms"
