"""
core/octos_agent_bus.py
========================
Octos Multi-Channel Agentic Coordination Bus for J.A.R.V.I.S.
Adapted from octos-org/octos:
  1. Central event bus unifying WhatsApp, Discord, Terminal, and Dashboard channels.
  2. Master Muhammad Qureshi cross-channel session context synchronization.
  3. Structured publish-subscribe event routing with in-memory buffer and persistence.
  4. Multi-asset conversational command dispatch (Crypto, Memes, Forex, Funded Accounts).
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Callable
import time
import uuid
import logging

logger = logging.getLogger("Jarvis.OctosBus")

CHANNELS = ["WHATSAPP", "DISCORD", "TERMINAL", "DASHBOARD", "SPATIAL_CAM"]

@dataclass
class OctosEvent:
    event_id: str
    channel: str       # WHATSAPP, DISCORD, TERMINAL, DASHBOARD, etc.
    event_type: str    # MESSAGE_INCOMING, TRADE_SIGNAL, APPROVAL_REQUEST, APPROVAL_RESOLVED, SYSTEM_ALERT
    sender: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class OctosAgentBus:
    """
    Autonomous multi-channel coordination OS.
    """
    def __init__(self, max_history: int = 500):
        self.max_history = max_history
        self.subscribers: Dict[str, List[Callable[[OctosEvent], None]]] = {}
        self.event_history: List[OctosEvent] = []
        self.master_active_channel: str = "WHATSAPP"
        self.conversation_turn_count: int = 0

    def subscribe(self, event_type: str, handler: Callable[[OctosEvent], None]):
        """Subscribes a listener to a specific event topic or '*' for all events."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)

    def publish(self, channel: str, event_type: str, sender: str, payload: Dict[str, Any]) -> OctosEvent:
        """Publishes an event across the coordinated channels."""
        event_id = f"oct_{uuid.uuid4().hex[:8]}"
        event = OctosEvent(
            event_id=event_id,
            channel=channel.upper(),
            event_type=event_type.upper(),
            sender=sender,
            payload=payload,
        )

        # Track active channel if sender is Master Muhammad Qureshi
        if "Muhammad" in sender or "Qureshi" in sender or sender in ("+923468053268", "Master"):
            self.master_active_channel = channel.upper()
            self.conversation_turn_count += 1

        # Maintain ring buffer
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Dispatch to specific subscribers
        handlers = self.subscribers.get(event.event_type, []) + self.subscribers.get("*", [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.exception("Error in Octos subscriber handler for %s: %s", event_type, e)

        return event

    def dispatch_broadcast(
        self,
        event_type: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        target_channels: Optional[List[str]] = None,
    ) -> List[OctosEvent]:
        """
        Dispatches a broadcast message simultaneously to designated channels.
        """
        targets = target_channels or ["WHATSAPP", "DISCORD", "TERMINAL", "DASHBOARD"]
        events = []
        payload = {"message": message, "metadata": metadata or {}}

        for ch in targets:
            ev = self.publish(
                channel=ch,
                event_type=event_type,
                sender="J.A.R.V.I.S.",
                payload=payload,
            )
            events.append(ev)

        return events

    def get_recent_events(self, channel: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetches latest events for display in Master Dashboard or Terminal."""
        filtered = self.event_history
        if channel:
            ch_upper = channel.upper()
            filtered = [e for e in self.event_history if e.channel == ch_upper]
        return [e.to_dict() for e in filtered[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        return {
            "bus": "OctosMultiChannelBus_v1",
            "active_channels": CHANNELS,
            "master_active_channel": self.master_active_channel,
            "total_events_processed": len(self.event_history),
            "conversation_turn_count": self.conversation_turn_count,
            "registered_subscribers": sum(len(h) for h in self.subscribers.values()),
        }


_global_bus: Optional[OctosAgentBus] = None

def get_octos_agent_bus() -> OctosAgentBus:
    global _global_bus
    if _global_bus is None:
        _global_bus = OctosAgentBus()
    return _global_bus
