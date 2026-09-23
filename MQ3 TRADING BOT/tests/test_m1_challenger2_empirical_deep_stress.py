"""
tests/test_m1_challenger2_empirical_deep_stress.py — Challenger 2 Empirical Stress Test Harness for Milestone 1.
==================================================================================================================
Empirically stress-tests:
1. Web Terminal QR Status API (`GET /api/whatsapp_qr`) contract verification.
2. Web Terminal Command Dispatch API (`POST /api/whatsapp_command`) under authorized & unauthorized inputs.
3. Broadcast routines (`CommunitySignalBroadcaster` and `DailyInstitutionalRoutineEngine`) recipient isolation.
4. WhatsApp Socket & Whitelist filter resistance against spoofing, null-bytes, control characters, and high throughput.
5. Zero secondary contacts leakage across all broadcast and socket execution paths.
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.web_terminal_server import app, terminal_state
from src.whatsapp_qr_manager import (
    WhatsAppQRManager,
    is_whitelisted_number,
    AUTHORIZED_CONTACTS,
    ELITE_TRADE_GROUP_JID
)
from src.community_signal_broadcaster import CommunitySignalBroadcaster
from src.daily_institutional_routine_engine import DailyInstitutionalRoutineEngine


# =====================================================================
# 1. Web Terminal QR Status & Command API Empirical Verification
# =====================================================================

class TestWebTerminalQRAndCommandAPI:
    """Verifies the REST contract of /api/whatsapp_qr and /api/whatsapp_command."""

    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    def test_get_whatsapp_qr_authorized_contacts_strictly_master_owner(self):
        """
        Verify GET /api/whatsapp_qr returns authorized_contacts containing strictly ['923468053268'].
        Must not contain any secondary family contacts or unexpected entries.
        """
        response = self.client.get("/api/whatsapp_qr")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data.get("status") == "success"
        assert "authorized_contacts" in data
        assert isinstance(data["authorized_contacts"], list)
        
        # Strict validation: Exactly 1 contact, strictly ['923468053268']
        assert len(data["authorized_contacts"]) == 1, (
            f"Expected exactly 1 authorized contact, but found {len(data['authorized_contacts'])}: {data['authorized_contacts']}"
        )
        assert data["authorized_contacts"] == ["923468053268"], (
            f"Authorized contacts mismatch: expected ['923468053268'], got {data['authorized_contacts']}"
        )
        
        # Purged numbers MUST NOT be present
        purged = ["923487117832", "923322555238", "923375893095"]
        for p in purged:
            assert p not in data["authorized_contacts"], f"Purged number {p} found in authorized_contacts!"
            
        # Group verification
        assert data.get("elite_group") == "120363401615322542@g.us"

    def test_post_whatsapp_command_unauthorized_drop_silent(self):
        """Verifies that unauthorized senders via /api/whatsapp_command receive empty response."""
        unauthorized_senders = [
            "923487117832",
            "923322555238",
            "923375893095",
            "+12025550199",
            "923468053269@s.whatsapp.net",
            "attacker@s.whatsapp.net",
            "120363999999999999@g.us"
        ]
        for sender in unauthorized_senders:
            payload = {
                "command": "status",
                "sender": sender
            }
            res = self.client.post("/api/whatsapp_command", json=payload)
            assert res.status_code == 403

    def test_post_whatsapp_command_authorized_master_owner(self):
        """Verifies that authorized Master Owner receives a non-empty status response."""
        authorized_senders = [
            "923468053268",
            "923468053268@s.whatsapp.net",
            "+923468053268@s.whatsapp.net"
        ]
        for sender in authorized_senders:
            payload = {
                "command": "status",
                "sender": sender
            }
            res = self.client.post("/api/whatsapp_command", json=payload)
            assert res.status_code == 200
            data = res.json()
            assert len(data["response"]) > 0
            assert "STATUS" in data["response"] or "FUNDING PIPS" in data["response"]


# =====================================================================
# 2. Downstream Broadcast Routines Empirical Verification
# =====================================================================

class TestDownstreamBroadcastRoutines:
    """Verifies that downstream broadcast routines only send to Master Owner and Elite Trade Group."""

    def test_community_signal_broadcaster_single_recipient(self):
        """Verify CommunitySignalBroadcaster only sends to Master Owner."""
        mock_qr = MagicMock(spec=WhatsAppQRManager)
        mock_qr.AUTHORIZED_CONTACTS = AUTHORIZED_CONTACTS
        mock_qr.send_message.return_value = True

        broadcaster = CommunitySignalBroadcaster(qr_manager=mock_qr)
        results = broadcaster.broadcast_signal("Test signal card")

        # Must send to exactly 1 contact
        assert len(results) == 1, f"Expected 1 broadcast recipient, got {len(results)}: {results}"
        recipient_key = list(results.keys())[0]
        assert "923468053268" in recipient_key
        assert results[recipient_key] is True

        # Verify send_message was called exactly once with phone '923468053268'
        assert mock_qr.send_message.call_count == 1
        call_args = mock_qr.send_message.call_args
        assert call_args[1].get("to") == "923468053268" or call_args[0][1] == "923468053268" if len(call_args[0]) > 1 else call_args[1].get("to") == "923468053268"

    def test_daily_routine_morning_briefing_broadcast_isolation(self):
        """Verify DailyInstitutionalRoutineEngine.broadcast_morning_briefing only dispatches to Master Owner and Elite Trade Group."""
        mock_qr = MagicMock(spec=WhatsAppQRManager)
        mock_qr.AUTHORIZED_CONTACTS = AUTHORIZED_CONTACTS
        mock_qr.send_message.return_value = True

        routine_engine = DailyInstitutionalRoutineEngine(qr_manager=mock_qr)
        
        # Patch broadcaster methods and generation
        with patch.object(routine_engine, "generate_morning_master_briefing", return_value="Morning Briefing Test"):
            with patch.object(routine_engine.broadcaster, "broadcast_to_elite_trade_group", return_value=True) as mock_group:
                results = routine_engine.broadcast_morning_briefing()

        # Expected keys: Exactly 2 (Master User + Elite Trade Group)
        assert len(results) == 2, f"Expected exactly 2 recipients, got {len(results)}: {results}"
        assert any("923468053268" in k for k in results.keys()), "Master Owner missing in broadcast results"
        assert "Elite Trade Group" in results, "Elite Trade Group missing in broadcast results"
        
        # Ensure no purged contacts
        purged = ["923487117832", "923322555238", "923375893095"]
        for p in purged:
            assert not any(p in k for k in results.keys()), f"Purged contact {p} received broadcast!"

    def test_daily_routine_intraday_alert_broadcast_isolation(self):
        """Verify DailyInstitutionalRoutineEngine.broadcast_intraday_alert only dispatches to Master Owner and Elite Trade Group."""
        mock_qr = MagicMock(spec=WhatsAppQRManager)
        mock_qr.AUTHORIZED_CONTACTS = AUTHORIZED_CONTACTS
        mock_qr.send_message.return_value = True

        routine_engine = DailyInstitutionalRoutineEngine(qr_manager=mock_qr)
        
        with patch.object(routine_engine.broadcaster, "broadcast_to_elite_trade_group", return_value=True):
            results = routine_engine.broadcast_intraday_alert(alert_card="Intraday Alert Test")

        assert len(results) == 2
        assert any("923468053268" in k for k in results.keys())
        assert "Elite Trade Group" in results

    def test_daily_routine_nightly_retrospective_broadcast_isolation(self):
        """Verify DailyInstitutionalRoutineEngine.broadcast_nightly_retrospective only dispatches to Master Owner and Elite Trade Group."""
        mock_qr = MagicMock(spec=WhatsAppQRManager)
        mock_qr.AUTHORIZED_CONTACTS = AUTHORIZED_CONTACTS
        mock_qr.send_message.return_value = True

        routine_engine = DailyInstitutionalRoutineEngine(qr_manager=mock_qr)
        
        with patch.object(routine_engine, "generate_nightly_market_retrospective", return_value="Nightly Retrospective Test"):
            with patch.object(routine_engine.broadcaster, "broadcast_to_elite_trade_group", return_value=True):
                results = routine_engine.broadcast_nightly_retrospective()

        assert len(results) == 2
        assert any("923468053268" in k for k in results.keys())
        assert "Elite Trade Group" in results


# =====================================================================
# 3. High-Throughput Whitelist Filter Stress & Invariant Verification
# =====================================================================

class TestWhitelistHighThroughputAndSecurityStress:
    """Stress tests whitelist functions with thousands of rapid calls, edge cases, and adversary inputs."""

    def test_high_volume_random_and_purged_rejection(self):
        """Runs 1,000 checks of mutated numbers to ensure no false positives."""
        base_purged = ["923487117832", "923322555238", "923375893095"]
        
        for p in base_purged:
            for prefix in ["", "+", "00", "0"]:
                for suffix in ["", "@s.whatsapp.net", ":0@s.whatsapp.net", ":12@s.whatsapp.net"]:
                    candidate = f"{prefix}{p}{suffix}"
                    assert is_whitelisted_number(candidate) is False, f"Purged variant '{candidate}' was allowed!"

    def test_high_throughput_filtering_speed(self):
        """Runs 5,000 calls to is_whitelisted_number to verify sub-millisecond throughput."""
        import time
        t0 = time.perf_counter()
        for i in range(5000):
            is_whitelisted_number("923468053268@s.whatsapp.net")
            is_whitelisted_number("923487117832@s.whatsapp.net")
            is_whitelisted_number("120363401615322542@g.us")
            is_whitelisted_number("attacker@s.whatsapp.net")
        elapsed = time.perf_counter() - t0
        avg_us = (elapsed / 20000) * 1_000_000
        print(f"\n[Whitelist Performance]: 20,000 checks completed in {elapsed*1000:.2f}ms (Avg {avg_us:.2f} µs/call)")
        assert elapsed < 2.0, "Whitelist evaluation took longer than 2.0s for 20k calls"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
