"""Explicit, owner-reviewed outbound messages via the local Baileys bridge."""
import json
import os
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]


def send_reviewed_message(recipient, message):
    try:
        token = os.getenv("JARVIS_WA_HTTP_TOKEN", "")
        if not token:
            token = json.loads((ROOT / "config/wa.local.json").read_text(encoding="utf-8")).get("http_token", "")
        if not token:
            return {"ok": False, "executed": False, "output": "WhatsApp local authorization is not configured."}
        response = requests.post("http://127.0.0.1:3200/send", headers={"X-Jarvis-Token": token},
                                 json={"number": recipient, "message": message}, timeout=(2, 20))
        data = response.json()
        if response.ok and data.get("ok") and data.get("message_id"):
            return {"ok": True, "executed": True, "message_id": data["message_id"], "delivered": False,
                    "output": "WhatsApp accepted the message and returned a message ID. Recipient delivery/read status is not verified."}
        return {"ok": False, "executed": False, "output": "WhatsApp did not confirm sending: " + str(data.get("error", "no message receipt"))[:160]}
    except requests.Timeout:
        return {"ok": False, "executed": None, "delivery_unknown": True,
                "output": "WhatsApp send timed out. Delivery is unknown; check the conversation before retrying."}
    except (OSError, ValueError, requests.RequestException) as exc:
        return {"ok": False, "executed": False, "output": "WhatsApp request failed: " + type(exc).__name__}
