"""
tests/test_octos_bus.py
========================
Verification for Octos multi-channel agentic coordination bus.
"""

import pytest
from core.octos_agent_bus import OctosAgentBus, get_octos_agent_bus

class TestOctosBus:
    def test_publish_and_subscribe(self):
        bus = OctosAgentBus()
        received_events = []

        def on_trade_signal(event):
            received_events.append(event)

        bus.subscribe("TRADE_SIGNAL", on_trade_signal)

        event = bus.publish(
            channel="TERMINAL",
            event_type="TRADE_SIGNAL",
            sender="AI_Trader_Scout",
            payload={"symbol": "XAUUSD", "action": "BUY", "risk_pct": 0.50},
        )

        assert len(received_events) == 1
        assert received_events[0].event_id == event.event_id
        assert received_events[0].payload["symbol"] == "XAUUSD"

    def test_broadcast_multi_channel(self):
        bus = OctosAgentBus()
        broadcasts = bus.dispatch_broadcast(
            event_type="MORNING_BRIEFING",
            message="Good morning Master Muhammad Qureshi Sir. Market playbook ready.",
            metadata={"priority": "HIGH"},
            target_channels=["WHATSAPP", "DISCORD", "TERMINAL"],
        )

        assert len(broadcasts) == 3
        channels = [b.channel for b in broadcasts]
        assert "WHATSAPP" in channels
        assert "DISCORD" in channels
        assert "TERMINAL" in channels

    def test_master_active_channel_tracking(self):
        bus = OctosAgentBus()
        bus.publish(
            channel="WHATSAPP",
            event_type="MESSAGE_INCOMING",
            sender="+923468053268",
            payload={"text": "Jarvis, gold ka status kya hai?"},
        )
        assert bus.master_active_channel == "WHATSAPP"
        assert bus.conversation_turn_count >= 1

        # Master switches to Discord
        bus.publish(
            channel="DISCORD",
            event_type="MESSAGE_INCOMING",
            sender="Master Muhammad Qureshi",
            payload={"text": "Discord par bhi active raho."},
        )
        assert bus.master_active_channel == "DISCORD"
        assert bus.conversation_turn_count >= 2

    def test_zero_prohibited_identifer(self):
        bus = OctosAgentBus()
        status = bus.get_status()
        dump = str(status).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump
