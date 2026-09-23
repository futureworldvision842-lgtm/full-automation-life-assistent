"""
tests/test_opendroid_bridge.py
===============================
Verification for OpenDroid mobile bridge and "Yeh Dabao" human verification.
"""

import pytest
import time
from mobile.opendroid_bridge import OpenDroidBridge, get_opendroid_bridge

class TestOpenDroidBridge:
    def test_token_creation_and_expiration(self):
        bridge = OpenDroidBridge(default_ttl_seconds=2)
        token = bridge.create_verification_request(
            action_type="EXECUTE_GOLD_TRADE",
            summary_en="Execute BUY on XAUUSD with 0.50% risk ($500).",
            summary_urdu="XAUUSD par BUY trade 0.50% risk par lagani hai.",
            metadata={"symbol": "XAUUSD", "lot_size": 0.5},
            ttl_seconds=1,
        )

        assert token.token_id.startswith("HVT-")
        assert token.status == "PENDING"
        assert token.is_valid() is True

        # Wait for expiration
        time.sleep(1.1)
        assert token.is_valid() is False

        # Attempt verification on expired token
        res = bridge.verify_token(token.token_id, decision="approve")
        assert res["success"] is False
        assert res["status"] == "EXPIRED"

    def test_token_approval_with_yeh_dabao(self):
        bridge = OpenDroidBridge(default_ttl_seconds=60)
        callback_called = []

        def on_approved(t):
            callback_called.append(t.token_id)

        token = bridge.create_verification_request(
            action_type="HIGH_LEVERAGE_MEME_TRADE",
            summary_en="Authorize PEPE trade on DEX.",
            summary_urdu="PEPE coin trade verify karein.",
            on_approved=on_approved,
        )

        # Approve using "yeh_dabao" decision
        res = bridge.verify_token(token.token_id, decision="yeh_dabao", actor="Master Muhammad Qureshi")
        assert res["success"] is True
        assert res["status"] == "APPROVED"
        assert "Yeh Dabao" in res["message"]
        assert len(callback_called) == 1
        assert callback_called[0] == token.token_id

        # Secondary verification should fail (already approved)
        res2 = bridge.verify_token(token.token_id, decision="yeh_dabao")
        assert res2["success"] is False
        assert res2["status"] == "APPROVED"

    def test_token_rejection(self):
        bridge = OpenDroidBridge(default_ttl_seconds=60)
        token = bridge.create_verification_request(
            action_type="UNAUTHORIZED_API_CALL",
            summary_en="Reboot cluster node",
            summary_urdu="Node restart karni hai",
        )
        res = bridge.verify_token(token.token_id, decision="reject", actor="Master Muhammad Qureshi")
        assert res["success"] is True
        assert res["status"] == "REJECTED"

    def test_whatsapp_message_formatting(self):
        bridge = OpenDroidBridge()
        token = bridge.create_verification_request(
            action_type="XAUUSD_BREAKOUT_CONFIRMATION",
            summary_en="Confirm Gold order at 2650",
            summary_urdu="Gold order 2650 par tasdeeq karein",
        )
        msg = bridge.format_whatsapp_approval_message(token, base_url="http://localhost:8770")
        assert "YEH DABAO" in msg
        assert token.token_id in msg
        assert "Master Muhammad Qureshi Sir" in msg

    def test_adb_simulated_touch_commands(self):
        bridge = OpenDroidBridge()
        tap_res = bridge.tap(500, 1000)
        assert tap_res["success"] is True

        swipe_res = bridge.swipe(200, 800, 200, 200)
        assert swipe_res["success"] is True

        status = bridge.get_device_status()
        assert status["bridge"] == "OpenDroid_ADB_v2"
        assert status["owner"] == "Master Muhammad Qureshi"

    def test_zero_prohibited_identifer(self):
        bridge = OpenDroidBridge()
        t = bridge.create_verification_request("TEST_ACTION", "Test En", "Test Urdu")
        msg = bridge.format_whatsapp_approval_message(t)
        dump = (str(t.to_dict()) + msg).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump
