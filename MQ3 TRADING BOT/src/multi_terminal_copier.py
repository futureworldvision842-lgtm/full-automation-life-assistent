"""Verified multi-terminal execution coordinator.

MetaTrader's Python integration controls one connected terminal/account at a
time.  A four-account fleet therefore needs four independently configured
terminal connectors.  This module refuses to claim replication unless every
reported execution comes from the connector bound to that exact account.
"""

from __future__ import annotations

from datetime import datetime, timezone
import math
import random
import time
from typing import Any, Dict, List, Optional

from src.live_readiness import LiveReadinessManager
from src.signal_quality_gate import SignalQualityGate
from src.trade_admission import TradeAdmissionGate


class MultiTerminalCopier:
    MAX_ORDER_LOTS = 5.0

    def __init__(
        self,
        fleet_config: Optional[Dict[str, Any]] = None,
        *,
        connectors: Optional[Dict[str, Any]] = None,
        simulation_mode: bool = True,
        readiness_manager: Optional[LiveReadinessManager] = None,
        admission_gate: Optional[TradeAdmissionGate] = None,
        signal_quality_gate: Optional[SignalQualityGate] = None,
    ):
        self.fleet_config = fleet_config or self._default_fleet()
        self.connectors: Dict[str, Any] = {str(key): value for key, value in (connectors or {}).items()}
        self.simulation_mode = bool(simulation_mode)
        self.readiness = readiness_manager or LiveReadinessManager()
        self.admission_gate = admission_gate or TradeAdmissionGate()
        self.signal_quality_gate = signal_quality_gate or SignalQualityGate()
        self.replication_log: List[Dict[str, Any]] = []

    @staticmethod
    def _default_fleet() -> Dict[str, Any]:
        return {
            "master_account": None,
            "mode": "PLANNED_PAPER_FLEET",
            "accounts": {
                "planned_5k": {"account_id": None, "account_name": "$5K planned evaluation", "balance": 5000.0, "risk_pct": 0.0025, "is_active": False},
                "planned_25k": {"account_id": None, "account_name": "$25K planned evaluation", "balance": 25000.0, "risk_pct": 0.0025, "is_active": False},
                "planned_50k": {"account_id": None, "account_name": "$50K planned evaluation", "balance": 50000.0, "risk_pct": 0.0025, "is_active": False},
                "planned_100k": {"account_id": None, "account_name": "$100K planned evaluation", "balance": 100000.0, "risk_pct": 0.0025, "is_active": False},
            },
        }

    def register_connector(self, account_id: Any, connector: Any) -> Dict[str, Any]:
        """Bind one connector to one account after verifying its reported login."""
        expected = str(account_id).strip()
        if not expected or connector is None or not hasattr(connector, "get_account_info"):
            return {"success": False, "reason": "A valid account_id and connector are required"}
        info = connector.get_account_info()
        reported = str(info.get("login")) if isinstance(info, dict) and info.get("login") is not None else ""
        is_paper = bool(getattr(connector, "simulation_mode", False))
        if not is_paper and (not info.get("available") or reported != expected):
            return {"success": False, "reason": "Connector login does not match the requested account", "reported_login": reported or None}
        self.connectors[expected] = connector
        return {"success": True, "account_id": expected, "mode": "PAPER" if is_paper else "LIVE", "reported_login": reported or None}

    def calculate_slave_lot_size(self, symbol: str, master_volume: float, target_account_key: str, sl_pips: float = 12.0) -> float:
        account = self.fleet_config.get("accounts", {}).get(target_account_key)
        if not account or not account.get("is_active"):
            return 0.0
        balance = float(account.get("balance", 0.0))
        risk_pct = float(account.get("risk_pct", 0.0025))
        if balance <= 0 or not 0 < risk_pct <= 0.01:
            return 0.0
        clean = str(symbol).upper().replace("/", "")
        pip_value = 10.0
        if "XAU" in clean or "GOLD" in clean:
            pip_value = 10.0
        elif "JPY" in clean:
            pip_value = 6.5
        elif any(token in clean for token in ("BTC", "ETH", "SOL")):
            pip_value = 1.0
        distance = float(sl_pips)
        if not math.isfinite(distance) or distance <= 0:
            return 0.0
        lots = (balance * risk_pct) / (distance * pip_value)
        return round(min(max(lots, 0.01), self.MAX_ORDER_LOTS), 2)

    @staticmethod
    def _connector_matches_account(connector: Any, account_id: str) -> bool:
        if bool(getattr(connector, "simulation_mode", False)):
            return True
        try:
            info = connector.get_account_info()
        except Exception:
            return False
        return bool(info.get("available") and str(info.get("login")) == account_id)

    def replicate_order(self, master_trade_data: Dict[str, Any], mt5_connector: Any = None) -> Dict[str, Any]:
        """Dispatch to explicitly bound connectors and report only authentic receipts."""
        symbol = str(master_trade_data.get("symbol", "")).upper().strip()
        side = str(master_trade_data.get("signal_type", master_trade_data.get("direction", ""))).upper().strip()
        try:
            entry = float(master_trade_data.get("entry_price"))
            sl = float(master_trade_data.get("sl_price", master_trade_data.get("sl")))
            tp = float(master_trade_data.get("tp_price", master_trade_data.get("tp")))
            sl_pips = float(master_trade_data.get("sl_pips", 0.0))
        except (TypeError, ValueError):
            return {"success": False, "status": "REJECTED", "reason": "Numeric entry, SL, TP, and sl_pips are required", "slave_executions": {}}
        geometry = (side == "BUY" and sl < entry < tp) or (side == "SELL" and tp < entry < sl)
        if not symbol or not geometry or not all(math.isfinite(value) and value > 0 for value in (entry, sl, tp, sl_pips)):
            return {"success": False, "status": "REJECTED", "reason": "Invalid symbol or SL/entry/TP geometry", "slave_executions": {}}

        output: Dict[str, Any] = {
            "success": False,
            "status": "NO_EXECUTIONS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": symbol,
            "signal_type": side,
            "slave_executions": {},
            "total_fleet_volume": 0.0,
        }
        total_volume = 0.0
        successes = 0
        for account_key, meta in self.fleet_config.get("accounts", {}).items():
            if not meta.get("is_active"):
                continue
            account_id = str(meta.get("account_id") or "").strip()
            result = {"account_name": meta.get("account_name"), "account_id": account_id or None, "success": False}
            if not account_id:
                result.update({"status": "REJECTED_UNBOUND_ACCOUNT", "reason": "Account login has not been configured"})
                output["slave_executions"][account_key] = result
                continue
            connector = self.connectors.get(account_id)
            if connector is None and mt5_connector is not None and self._connector_matches_account(mt5_connector, account_id):
                connector = mt5_connector
            if connector is None:
                result.update({"status": "REJECTED_NO_CONNECTOR", "reason": "No terminal connector is bound to this account"})
                output["slave_executions"][account_key] = result
                continue
            if not self._connector_matches_account(connector, account_id):
                result.update({"status": "REJECTED_ACCOUNT_MISMATCH", "reason": "Connected terminal login does not match account"})
                output["slave_executions"][account_key] = result
                continue

            connector_is_live = not bool(getattr(connector, "simulation_mode", False))
            if connector_is_live:
                allowed, blockers = self.readiness.live_execution_allowed(account_id, autonomous=True)
                if not allowed:
                    result.update({"status": "REJECTED_NOT_LIVE_READY", "reason": "; ".join(blockers)})
                    output["slave_executions"][account_key] = result
                    continue
                admitted, admission_reasons = self.admission_gate.evaluate(master_trade_data.get("market_context"), live=True)
                if not admitted:
                    result.update({"status": "REJECTED_MARKET_CONTEXT", "reason": "; ".join(admission_reasons)})
                    output["slave_executions"][account_key] = result
                    continue
                quality_ok, quality_reasons = self.signal_quality_gate.evaluate(master_trade_data.get("market_context"), live=True)
                if not quality_ok:
                    result.update({"status": "REJECTED_SIGNAL_QUALITY", "reason": "; ".join(quality_reasons)})
                    output["slave_executions"][account_key] = result
                    continue

            lots = self.calculate_slave_lot_size(symbol, float(master_trade_data.get("volume", 0.0) or 0.0), account_key, sl_pips)
            if lots <= 0:
                result.update({"status": "REJECTED_RISK_SIZE", "reason": "Risk-calibrated lot size is zero"})
                output["slave_executions"][account_key] = result
                continue
            execution_context = ({
                "executor": "MultiTerminalCopier",
                "account_id": account_id,
                "readiness_passed": True,
                "risk_passed": True,
                "market_admission_passed": True,
                "signal_quality_passed": True,
                "issued_at": datetime.now(timezone.utc).isoformat(),
            } if connector_is_live else None)
            order_kwargs = {
                "symbol": symbol, "signal_type": side, "volume": lots,
                "price": entry, "sl": sl, "tp": tp, "comment": f"MQ3-{account_key}",
            }
            if execution_context is not None:
                order_kwargs["execution_context"] = execution_context

            # Anti-collision execution jitter: Avoid identical millisecond execution signature across accounts
            if successes > 0 and not self.simulation_mode:
                time.sleep(random.uniform(0.15, 0.45))

            receipt = connector.place_order(**order_kwargs)
            ok = bool(isinstance(receipt, dict) and receipt.get("success") and receipt.get("ticket"))
            result.update({"success": ok, "status": "FILLED" if ok else "FAILED", "allocated_lot": lots, "ticket": receipt.get("ticket") if isinstance(receipt, dict) else None, "receipt": receipt})
            output["slave_executions"][account_key] = result
            if ok:
                successes += 1
                total_volume += lots

        output["success"] = successes > 0
        output["status"] = "FILLED" if successes and successes == len(output["slave_executions"]) else ("PARTIAL" if successes else "NO_EXECUTIONS")
        output["total_fleet_volume"] = round(total_volume, 2)
        output["executed_accounts"] = successes
        self.replication_log.append(output)
        return output

    def get_fleet_telemetry(self) -> Dict[str, Any]:
        accounts = self.fleet_config.get("accounts", {})
        configured = [meta for meta in accounts.values() if meta.get("account_id")]
        active = [meta for meta in accounts.values() if meta.get("is_active")]
        return {
            "mode": self.fleet_config.get("mode", "UNVERIFIED"),
            "total_planned_aum": sum(float(meta.get("balance", 0.0)) for meta in accounts.values()),
            "active_accounts_count": len(active),
            "configured_accounts_count": len(configured),
            "bound_connectors_count": len(self.connectors),
            "replications_count": len(self.replication_log),
            "fleet_accounts": accounts,
            "live_ready": bool(active) and len(self.connectors) >= len(active),
            "warning": "Each live account requires its own verified terminal connector; no execution is inferred or fabricated.",
        }
