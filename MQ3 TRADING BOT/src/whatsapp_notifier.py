"""Truthful WhatsApp delivery for verified execution receipts.

This notifier does not generate market analysis.  It formats values already
confirmed by a paper/demo/live connector and reports delivery only when the
local WhatsApp bridge acknowledges the message.
"""

from __future__ import annotations

import json
import logging
import math
import os
from typing import Any, Dict

import requests


logger = logging.getLogger(__name__)


class WhatsAppNotifier:
    BRIDGE_URL = "http://127.0.0.1:3001"

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.phone_number = "923468053268"
        self.api_key = ""
        self.is_connected = False
        self.load_config()

    def load_config(self) -> None:
        if not os.path.exists(self.config_path):
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                cfg = json.load(handle)
            wa_cfg = cfg.get("whatsapp", {}) if isinstance(cfg, dict) else {}
            self.phone_number = str(wa_cfg.get("phone_number", self.phone_number))
            self.api_key = os.environ.get("WHATSAPP_API_KEY", "")
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("WhatsApp config unavailable: %s", exc)

    def set_whatsapp_credentials(self, phone: str, api_key: str = "") -> bool:
        self.phone_number = str(phone or "").strip()
        if api_key:
            self.api_key = str(api_key).strip()
        logger.info("WhatsApp runtime credentials updated for phone ending %s", self.phone_number[-4:])
        return bool(self.phone_number)

    @staticmethod
    def _bridge_headers() -> Dict[str, str]:
        token = os.environ.get("MQ3_BRIDGE_TOKEN", "").strip()
        if not token:
            from pathlib import Path
            token_file = Path("runtime/bridge_token.txt")
            if token_file.exists():
                try:
                    token = token_file.read_text(encoding="utf-8-sig").replace("\ufeff", "").strip()
                except Exception:
                    pass
        return {"X-MQ3-Bridge-Token": token} if token else {}

    def start_qr_linking_async(self) -> None:
        logger.info("WhatsApp notifier initialized; bridge connection remains independently verified")

    def send_message(self, text_message: str) -> bool:
        """Return True only when the local bridge explicitly confirms delivery."""
        if not isinstance(text_message, str) or not text_message.strip():
            return False
        safe_log = text_message.encode("ascii", "replace").decode("ascii")
        logger.info("[WHATSAPP DELIVERY ATTEMPT]:\n%s", safe_log)
        try:
            response = requests.post(
                f"{self.BRIDGE_URL}/send_group",
                json={"group_name": "Elite Trade", "message": text_message},
                headers=self._bridge_headers(),
                timeout=8,
            )
            if response.status_code >= 400:
                return False
            payload = response.json()
            confirmed = bool(isinstance(payload, dict) and (payload.get("success") is True or payload.get("sent") is True))
            self.is_connected = confirmed
            return confirmed
        except Exception as exc:
            logger.debug("WhatsApp bridge did not confirm delivery: %s", exc)
            self.is_connected = False
            return False

    @staticmethod
    def _format_price(symbol: str, value: float) -> str:
        if any(token in symbol for token in ("XAU", "XAG", "BTC", "ETH", "SOL", "OIL", "WTI")):
            return f"{value:,.2f}"
        if "JPY" in symbol:
            return f"{value:,.3f}"
        return f"{value:.5f}"

    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """Send a connector receipt without inventing analysis or price levels."""
        if not isinstance(trade_data, dict):
            return False
        symbol = str(trade_data.get("symbol", "")).upper().strip()
        direction = str(trade_data.get("signal_type", trade_data.get("direction", ""))).upper().strip()
        receipt_id = trade_data.get("receipt_id") or trade_data.get("ticket") or trade_data.get("order_id")
        try:
            volume = float(trade_data.get("volume", trade_data.get("lots")))
            entry = float(trade_data.get("entry_price", trade_data.get("open_price")))
            stop = float(trade_data.get("sl_price", trade_data.get("sl")))
            target = float(trade_data.get("tp1_price", trade_data.get("tp_price", trade_data.get("tp1", trade_data.get("tp")))))
        except (TypeError, ValueError):
            return False
        if (
            not symbol
            or direction not in {"BUY", "SELL"}
            or not receipt_id
            or volume <= 0
            or not all(math.isfinite(value) and value > 0 for value in (volume, entry, stop, target))
        ):
            return False
        geometry_ok = (direction == "BUY" and stop < entry < target) or (direction == "SELL" and target < entry < stop)
        if not geometry_ok:
            return False

        data_mode = str(trade_data.get("data_mode", trade_data.get("mode", "UNVERIFIED"))).upper()
        risk_dollars = trade_data.get("risk_dollars")
        risk_line = "Unknown; verify the broker/account risk ledger before acting."
        try:
            numeric_risk = float(risk_dollars)
            if math.isfinite(numeric_risk) and numeric_risk >= 0:
                risk_line = f"${numeric_risk:,.2f} configured stop risk (fill/slippage not guaranteed)"
        except (TypeError, ValueError):
            pass

        message = (
            "*EXECUTION RECEIPT — VERIFY IN BROKER*\n"
            f"Receipt/Ticket: {receipt_id}\n"
            f"Mode: {data_mode}\n"
            f"Account: {trade_data.get('account_id', 'UNVERIFIED')}\n"
            f"Order: #{symbol} {direction} {volume:g} lots\n"
            f"Entry: {self._format_price(symbol, entry)}\n"
            f"Stop: {self._format_price(symbol, stop)}\n"
            f"Target: {self._format_price(symbol, target)}\n"
            f"Risk: {risk_line}\n"
            "A stop at/beyond entry is not risk-free: gaps, spread, slippage, commissions, swaps, and platform failure can still cause loss.\n"
            f"Commands: `be {symbol.lower()}` | `scale 50% {symbol.lower()}` | `close {symbol.lower()}`"
        )
        return bool(self.send_message(message))

    def send_full_intelligence_report(self) -> bool:
        """Refuse legacy fixed-number reports that are not broker reconciled."""
        return bool(self.send_message(
            "*ACCOUNT REPORT UNAVAILABLE*\n"
            "No broker-reconciled telemetry payload was supplied. Balance, profit, drawdown, win rate, and compliance were not inferred."
        ))
