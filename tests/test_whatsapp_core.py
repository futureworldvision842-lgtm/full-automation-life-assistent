"""
tests/test_whatsapp_core.py
============================
Verification for WhatsApp conversational core and daily alpha briefings.
"""

import pytest
from actions.whatsapp_conversational_core import WhatsAppConversationalCore, get_whatsapp_core
from mobile.opendroid_bridge import get_opendroid_bridge

class TestWhatsAppConversationalCore:
    def test_daily_alpha_briefing_content(self):
        core = get_whatsapp_core()
        briefing = core.generate_daily_alpha_briefing()

        assert "Master Muhammad Qureshi Sir" in briefing
        assert "FundingPips #40000294403" in briefing
        assert "<= 0.75% ($750 max loss)" in briefing
        assert "DAILY ALPHA" in briefing
        assert "adeel" not in briefing.lower()
        assert "qureshi99" not in briefing.lower()

    def test_dispatch_human_verification(self):
        core = get_whatsapp_core()
        bridge = get_opendroid_bridge()
        token = bridge.create_verification_request("TEST_ACTION", "Test En", "Test Urdu")

        res = core.dispatch_human_verification(token.token_id, "TEST_ACTION", "Test Urdu", "Test En")
        assert res["success"] is True

    def test_process_incoming_yeh_dabao(self):
        core = get_whatsapp_core()
        bridge = get_opendroid_bridge()
        token = bridge.create_verification_request("ORDER_BUY", "Buy gold", "Gold khareedo")

        reply = core.process_incoming_master_message("yeh dabao")
        assert "Tasdeeq Mukammal" in reply
        assert bridge.tokens[token.token_id].status == "APPROVED"

    def test_process_incoming_gold_query(self):
        core = get_whatsapp_core()
        reply = core.process_incoming_master_message("gold ka kya scene hai")
        assert "Gold (XAU/USD)" in reply
        assert "Confluence Score" in reply

    def test_zero_prohibited_identifer(self):
        core = get_whatsapp_core()
        reply1 = core.process_incoming_master_message("Salam Jarvis")
        reply2 = core.generate_daily_alpha_briefing()
        all_text = (reply1 + reply2).lower()
        assert "adeel" not in all_text
        assert "qureshi99" not in all_text
