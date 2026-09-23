"""
autonomous_fleet_executor.py — Multi-Account Autonomous Trade Execution & Reporting Engine.
=============================================================================================
Manages real-time automated trading across the entire curated fleet:
  1. Funding Pips 4k Challenge ($4,000 | $100 Daily Cap | $240 Trailing Floor)
  2. Funding Pips 25k Challenge ($25,000 | $625 Daily Cap | $1,500 Trailing Floor)
  3. Funding Pips 50k Challenge ($50,000 | $1,250 Daily Cap | $3,000 Trailing Floor)
  4. Funding Pips 100k Challenge ($100,000 | $2,500 Daily Cap | $6,000 Trailing Floor)
  5. Master MT5 Account #5054340275 ($10,000 | Personal Broker)
  6. Binance Crypto Scalp 5M ($1,000 | 24/7 Crypto Futures)
  7. Hyperliquid DEX On-Chain ($500 | Decentralized Perps)

Handles:
  • Pre-trade risk audits, dynamic lot sizing, and daily drawdown shields.
  • Automated trade entry on A+ SMC 70.5% OTE / CVD buyer absorption confluences.
  • Position management: 50% scale-out at TP1, Breakeven (+1 pip buffer) locking, Trailing FVG.
  • Automated trade execution notices and daily PnL summaries dispatched to client WhatsApp.
"""

import os
import time
import json
import logging
import math
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.fleet_risk_manager import FleetRiskManager
from src.whatsapp_qr_manager import WhatsAppQRManager
from src.bitget_connector import BitgetConnector
from src.mt5_connector import MT5Connector
from src.live_readiness import LiveReadinessManager
from src.trade_admission import TradeAdmissionGate
from src.signal_quality_gate import SignalQualityGate
from src.audit_ledger import AuditLedger

logger = logging.getLogger("AutonomousFleetExecutor")


class AutonomousFleetExecutor:
    """
    Autonomous Trade Execution & Reporting Engine for Multi-Account Fleet.
    Implements Project Interface Contract #2:
      route_order(account_id: str, order: Dict) -> ExecutionReceipt
    """

    def __init__(
        self,
        config_path: str = "data/fleet_config.json",
        risk_manager: Optional[FleetRiskManager] = None,
        whatsapp_manager: Optional[WhatsAppQRManager] = None,
        bitget_connector: Optional[BitgetConnector] = None,
        mt5_connector: Optional[MT5Connector] = None,
        mt5_connectors: Optional[Dict[str, MT5Connector]] = None,
        simulation_mode: bool = True,
        seed_demo_positions: Optional[bool] = None,
        readiness_manager: Optional[LiveReadinessManager] = None,
        admission_gate: Optional[TradeAdmissionGate] = None,
        signal_quality_gate: Optional[SignalQualityGate] = None,
        audit_ledger: Optional[AuditLedger] = None,
    ):
        self.config_path = config_path
        self.risk_manager = risk_manager or FleetRiskManager(config_path=self.config_path)
        self.whatsapp_manager = whatsapp_manager or WhatsAppQRManager()
        self.simulation_mode = bool(simulation_mode)
        self.bitget_connector = bitget_connector or BitgetConnector(sim_mode=self.simulation_mode)
        self.mt5_connector = mt5_connector or MT5Connector(simulation_mode=self.simulation_mode)
        self.mt5_connectors: Dict[str, MT5Connector] = {str(key): value for key, value in (mt5_connectors or {}).items()}
        self.readiness = readiness_manager or LiveReadinessManager()
        self.admission_gate = admission_gate or TradeAdmissionGate()
        self.signal_quality_gate = signal_quality_gate or SignalQualityGate()
        self.audit_ledger = audit_ledger or (AuditLedger() if not self.simulation_mode else None)
        self.active_positions: List[Dict[str, Any]] = []
        self.execution_history: List[Dict[str, Any]] = []
        if seed_demo_positions is True:
            self._init_benchmark_positions()

    def _init_benchmark_positions(self):
        """Initialize clearly labelled synthetic positions for dashboard demos/tests only."""
        self.active_positions = [
            {
                "ticket": 9841201,
                "account_id": "5054340275",
                "account_name": "Funding Pips 25k Challenge",
                "symbol": "XAUUSD",
                "type": "BUY",
                "direction": "BUY",
                "lots": 0.45,
                "open_price": 4432.00,
                "current_price": 4437.30,
                "sl": 4432.00,  # Breakeven locked
                "tp1": 4450.00,
                "tp2": 4475.00,
                "tp3": 4500.00,
                "profit": 238.50,
                "pips": 53.0,
                "reward_to_risk": "1:3.4",
                "wyckoff_phase": "WYCKOFF PHASE C (SPRING)",
                "smc_confluence": "50% FVG CE MITIGATED",
                "shark_attribution": "UNVERIFIED_DEMO_SCENARIO",
                "status": "BE_LOCKED",
                "data_mode": "SYNTHETIC_DEMO",
                "actionable": False,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "client_whatsapp": "+923468053268"
            },
            {
                "ticket": 9841202,
                "account_id": "FP_50K_DEMO",
                "account_name": "Funding Pips 50k Challenge",
                "symbol": "BTCUSD",
                "type": "SELL",
                "direction": "SELL",
                "lots": 0.50,
                "open_price": 63450.0,
                "current_price": 63330.0,
                "sl": 63450.0,  # Breakeven locked
                "tp1": 63000.0,
                "tp2": 62500.0,
                "tp3": 61800.0,
                "profit": 600.00,
                "pips": 120.0,
                "reward_to_risk": "1:3.2",
                "wyckoff_phase": "WYCKOFF PHASE D (SOS)",
                "smc_confluence": "PREMIUM BEARISH FVG REJECTION",
                "shark_attribution": "UNVERIFIED_DEMO_SCENARIO",
                "status": "BE_LOCKED",
                "data_mode": "SYNTHETIC_DEMO",
                "actionable": False,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "client_whatsapp": "+923468053268"
            },
            {
                "ticket": 9841203,
                "account_id": "BINANCE_SCALP_01",
                "account_name": "Binance Crypto Scalp 5M",
                "symbol": "BTCUSDT",
                "type": "SELL",
                "direction": "SELL",
                "lots": 0.05,
                "open_price": 63390.0,
                "current_price": 63330.0,
                "sl": 63390.0,
                "tp1": 63100.0,
                "tp2": 62800.0,
                "tp3": 62200.0,
                "profit": 30.00,
                "pips": 60.0,
                "reward_to_risk": "1:2.8",
                "wyckoff_phase": "5M CVD SELLER PRESSURE",
                "smc_confluence": "LONDON OPEN DISPATCH",
                "shark_attribution": "UNVERIFIED_DEMO_SCENARIO",
                "status": "RUNNING",
                "data_mode": "SYNTHETIC_DEMO",
                "actionable": False,
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "client_whatsapp": "+923468053268"
            }
        ]

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Returns all open positions across the fleet."""
        return self.active_positions

    def _record_receipt(self, receipt: Dict[str, Any]) -> None:
        self.execution_history.append(receipt)
        if self.audit_ledger is not None:
            try:
                self.audit_ledger.append("EXECUTION_RECEIPT", receipt)
            except Exception as exc:
                # An audit failure must be visible.  For a successful live order
                # the broker result cannot be undone here, so record the failure
                # in memory and force operator attention in the receipt.
                receipt["audit_ledger_error"] = f"{type(exc).__name__}: {exc}"
                receipt["requires_operator_attention"] = True
                logger.error("Execution audit ledger append failed: %s", exc)

    def register_mt5_connector(self, account_id: Any, connector: MT5Connector) -> Dict[str, Any]:
        """Bind an MT5 connector to exactly one reported login."""
        expected = str(account_id).strip()
        if not expected or connector is None:
            return {"success": False, "reason": "account_id and connector are required"}
        info = connector.get_account_info()
        if not connector.simulation_mode and (not info.get("available") or str(info.get("login")) != expected):
            return {"success": False, "reason": "Connected MT5 login does not match account_id", "reported_login": info.get("login")}
        self.mt5_connectors[expected] = connector
        return {"success": True, "account_id": expected, "mode": "PAPER" if connector.simulation_mode else "LIVE"}

    def route_order(self, account_id: str, order: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interface Contract #2:
        Routes order to MT5 for Forex/Commodities or to Bitget for Crypto.
        Returns authentic ExecutionReceipt.
        """
        symbol = str(order.get("symbol", "")).upper().strip()
        direction = str(order.get("direction", order.get("type", ""))).upper().strip()
        account_state = self.risk_manager.get_account_state(account_id) or {}
        account_type = str(account_state.get("account_type", "")).upper()
        exchange_account = account_type in {
            "BINANCE_SPOT", "BINANCE_FUTURES", "BITGET", "HYPERLIQUID",
            "SCALP_5M", "CRYPTO_EXCHANGE",
        }
        # Venue follows the registered account, not the symbol.  Funding Pips
        # BTC/ETH CFDs must remain on that account's isolated MT5 terminal.
        is_crypto = exchange_account
        venue = "BITGET" if exchange_account else "MT5"

        def reject(reason: str, parsed_lots: Any = None) -> Dict[str, Any]:
            receipt = {
                "success": False,
                "status": "REJECTED",
                "reason": reason,
                "receipt_id": f"RCPT-REJECTED-{account_id}-{time.time_ns()}",
                "account_id": account_id,
                "venue": venue,
                "symbol": symbol or None,
                "direction": direction or None,
                "lots": parsed_lots,
                "ticket": None,
                "order_id": None,
                "data_mode": "REJECTED",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._record_receipt(receipt)
            return receipt

        try:
            lots = float(order.get("lots", order.get("volume", order.get("size", 0.0))))
            entry_price = float(order.get("entry_price", order.get("open_price", order.get("price", 0.0))))
            sl = float(order.get("sl", 0.0))
            tp = float(order.get("tp", order.get("tp1", 0.0)))
        except (TypeError, ValueError):
            return reject("Order values must be numeric")
        comment = order.get("comment", f"Fleet-{account_id}")

        if not symbol or direction not in {"BUY", "SELL"}:
            return reject("A valid symbol and BUY/SELL direction are required", lots)
        if not all(math.isfinite(v) for v in (lots, entry_price, sl, tp)) or lots <= 0 or lots > 5.0:
            return reject("Order contains a non-finite value or volume outside (0, 5] lots", lots)
        if entry_price <= 0 or sl <= 0 or tp <= 0:
            return reject("Entry, SL, and TP must be positive", lots)
        valid_geometry = (direction == "BUY" and sl < entry_price < tp) or (direction == "SELL" and tp < entry_price < sl)
        if not valid_geometry:
            return reject("Invalid SL/entry/TP geometry", lots)

        if is_crypto:
            # Route to Bitget
            connector_live = not bool(getattr(self.bitget_connector, "sim_mode", True))
            if connector_live:
                if not account_state:
                    return reject("Live exchange account is not registered in the risk fleet", lots)
                approved, risk_reason = self.risk_manager.validate_pre_trade_risk(
                    account_id=account_id, symbol=symbol, lot_size=lots, side=direction,
                    entry_price=entry_price, sl_price=sl, tp_price=tp,
                )
                if not approved:
                    return reject("Live pre-trade risk blocked: " + risk_reason, lots)
                ready, readiness_reasons = self.readiness.live_execution_allowed(account_id, autonomous=True)
                if not ready:
                    return reject("Live readiness blocked: " + "; ".join(readiness_reasons), lots)
                admitted, admission_reasons = self.admission_gate.evaluate(order.get("market_context"), live=True)
                if not admitted:
                    return reject("Live market-context gate blocked: " + "; ".join(admission_reasons), lots)
                quality_ok, quality_reasons = self.signal_quality_gate.evaluate(order.get("market_context"), live=True)
                if not quality_ok:
                    return reject("Live signal-quality gate blocked: " + "; ".join(quality_reasons), lots)
            execution_context = ({
                "executor": "AutonomousFleetExecutor",
                "account_id": str(account_id),
                "readiness_passed": True,
                "risk_passed": True,
                "market_admission_passed": True,
                "signal_quality_passed": True,
                "issued_at": datetime.now(timezone.utc).isoformat(),
            } if connector_live else None)
            target_symbol = symbol.replace("USDT", "").replace("USD", "") + "USDT"
            bitget_res = self.bitget_connector.place_order(
                symbol=target_symbol,
                side=direction.lower(),
                size=lots,
                order_type="market" if entry_price == 0.0 else "limit",
                price=entry_price if entry_price > 0.0 else None,
                sl=sl if sl > 0.0 else None,
                tp=tp if tp > 0.0 else None,
                execution_context=execution_context,
            )

            connector_success = bitget_res.get("status") == "success" and bool(bitget_res.get("order_id"))
            order_id = bitget_res.get("order_id") if connector_success else None
            receipt = {
                "success": connector_success,
                "receipt_id": f"RCPT-BG-{account_id}-{time.time_ns()}",
                "account_id": account_id,
                "ticket": order_id,
                "order_id": order_id,
                "venue": "BITGET",
                "symbol": target_symbol,
                "direction": direction,
                "lots": lots,
                "size": lots,
                "entry_price": bitget_res.get("data", {}).get("entry_price", entry_price) if connector_success else entry_price,
                "sl": sl,
                "tp": tp,
                "status": "FILLED" if connector_success else "FAILED",
                "data_mode": bitget_res.get("mode", "UNKNOWN"),
                "raw_result": bitget_res,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            # Route to MetaTrader 5
            target_connector = self.mt5_connectors.get(str(account_id), self.mt5_connector)
            connector_live = not bool(getattr(target_connector, "simulation_mode", True))
            if connector_live:
                if not account_state:
                    return reject("Live MT5 account is not registered in the risk fleet", lots)
                account_info = target_connector.get_account_info()
                if not account_info.get("available") or str(account_info.get("login")) != str(account_id):
                    return reject("MT5 terminal is not bound to the requested account", lots)
                approved, risk_reason = self.risk_manager.validate_pre_trade_risk(
                    account_id=account_id, symbol=symbol, lot_size=lots, side=direction,
                    entry_price=entry_price, sl_price=sl, tp_price=tp,
                )
                if not approved:
                    return reject("Live pre-trade risk blocked: " + risk_reason, lots)
                ready, readiness_reasons = self.readiness.live_execution_allowed(account_id, autonomous=True)
                if not ready:
                    return reject("Live readiness blocked: " + "; ".join(readiness_reasons), lots)
                admitted, admission_reasons = self.admission_gate.evaluate(order.get("market_context"), live=True)
                if not admitted:
                    return reject("Live market-context gate blocked: " + "; ".join(admission_reasons), lots)
                quality_ok, quality_reasons = self.signal_quality_gate.evaluate(order.get("market_context"), live=True)
                if not quality_ok:
                    return reject("Live signal-quality gate blocked: " + "; ".join(quality_reasons), lots)

            execution_context = ({
                "executor": "AutonomousFleetExecutor",
                "account_id": str(account_id),
                "readiness_passed": True,
                "risk_passed": True,
                "market_admission_passed": True,
                "signal_quality_passed": True,
                "issued_at": datetime.now(timezone.utc).isoformat(),
            } if connector_live else None)

            mt5_res = target_connector.place_order(
                symbol=symbol,
                signal_type=direction,
                volume=lots,
                price=entry_price,
                sl=sl,
                tp=tp,
                comment=comment,
                execution_context=execution_context,
            )

            ticket = mt5_res.get("ticket") if mt5_res.get("success") else None
            receipt = {
                "success": mt5_res.get("success", False),
                "receipt_id": f"RCPT-MT5-{account_id}-{time.time_ns()}",
                "account_id": account_id,
                "ticket": ticket,
                "order_id": str(ticket) if ticket is not None else None,
                "venue": "MT5",
                "symbol": symbol,
                "direction": direction,
                "lots": lots,
                "size": lots,
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp,
                "status": "FILLED" if mt5_res.get("success") else "FAILED",
                "data_mode": mt5_res.get("mode", "UNKNOWN"),
                "raw_result": mt5_res,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        self._record_receipt(receipt)
        logger.info(f"[AutonomousFleetExecutor] Routed order to {receipt['venue']}: {receipt['receipt_id']} for Account #{account_id}")
        return receipt

    def execute_fleet_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl: float,
        tp1: float,
        tp2: float,
        tp3: float,
        confluence_tag: str = "70.5% OTE FVG MITIGATION",
        shark_tag: str = "UNVERIFIED MARKET-STRUCTURE INFERENCE",
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes a trade across all active accounts in the fleet with tailored lot sizing and dual-venue routing.
        """
        self.risk_manager.load_fleet()
        executed_orders = []
        rejected_orders = []

        for acc_key, st in self.risk_manager.accounts_state.items():
            if not st.get("is_active"):
                continue

            acc_id = st.get("account_id", acc_key)
            acc_name = st.get("account_name", f"Account #{acc_id}")
            bal = float(st.get("balance", st.get("starting_balance", 25000.0)))
            client_wa = st.get("client_whatsapp", "+923468053268")

            sl_dist = abs(entry_price - sl)
            lots = self.risk_manager.calculate_dynamic_lot_size(
                account_id=acc_id,
                symbol=symbol,
                entry_price=entry_price,
                sl_price=sl,
            )
            risk_pct = float(st.get("risk_per_trade_pct", 0.0075))
            normalized_risk_pct = risk_pct / 100.0 if risk_pct > 0.05 else risk_pct
            dollar_risk = bal * normalized_risk_pct

            approved, risk_reason = self.risk_manager.validate_pre_trade_risk(
                account_id=acc_id,
                symbol=symbol,
                lot_size=lots,
                side=direction,
                entry_price=entry_price,
                sl_price=sl,
                tp_price=tp1,
            )
            if not approved:
                rejected_orders.append({"account_id": acc_id, "status": "RISK_REJECTED", "reason": risk_reason})
                continue

            order_payload = {
                "symbol": symbol,
                "direction": direction.upper(),
                "lots": lots,
                "entry_price": entry_price,
                "sl": sl,
                "tp": tp1,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "comment": f"SMC-{acc_name[:12]}"
            }
            if market_context is not None:
                order_payload["market_context"] = market_context

            receipt = self.route_order(account_id=acc_id, order=order_payload)
            if not receipt.get("success"):
                rejected_orders.append({"account_id": acc_id, "status": "EXECUTION_FAILED", "reason": receipt.get("raw_result", receipt)})
                continue
            ticket = receipt.get("ticket")

            pos_entry = {
                "ticket": ticket,
                "account_id": acc_id,
                "account_name": acc_name,
                "symbol": symbol,
                "type": direction.upper(),
                "direction": direction.upper(),
                "lots": lots,
                "open_price": entry_price,
                "current_price": entry_price,
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "profit": 0.0,
                "pips": 0.0,
                "reward_to_risk": f"1:{round(abs(tp1 - entry_price) / max(0.1, sl_dist), 1)}",
                "wyckoff_phase": "WYCKOFF ACCUMULATION PHASE C",
                "smc_confluence": confluence_tag,
                "shark_attribution": shark_tag,
                "status": "RUNNING",
                "venue": receipt.get("venue", "MT5"),
                "data_mode": receipt.get("data_mode", "UNKNOWN"),
                "opened_at": datetime.now(timezone.utc).isoformat(),
                "client_whatsapp": client_wa
            }
            self.active_positions.append(pos_entry)
            self.risk_manager.register_open_position(
                acc_id,
                {
                    "ticket": ticket,
                    "symbol": symbol,
                    "side": direction.upper(),
                    "risk_dollars": abs(entry_price - sl) * self.risk_manager.get_contract_size(symbol) * lots,
                },
            )
            executed_orders.append(pos_entry)

            # Send a provenance-aware execution receipt if a client is registered.
            if client_wa and self.whatsapp_manager:
                try:
                    rr_1 = round(abs(tp1 - entry_price) / max(0.01, sl_dist), 1)
                    rr_2 = round(abs(tp2 - entry_price) / max(0.01, sl_dist), 1)
                    rr_3 = round(abs(tp3 - entry_price) / max(0.01, sl_dist), 1)
                    
                    wa_receipt = (
                        f"⚡ *NEW FLEET TRADE RECEIPT*\n"
                        f"═══════════════════════════════════════════════\n"
                        f"📌 *Account:* {acc_name} (#{acc_id}) | *Venue:* {receipt.get('venue')}\n"
                        f"🎯 *Asset:* #{symbol.upper()} | *Action:* STRONG {direction.upper()} ({lots} Lots)\n"
                        f"📈 *Entry Price:* {entry_price}\n"
                        f"🔴 *Stop Loss (SL):* {sl} (-${dollar_risk:.2f} exact risk | {sl_dist:.1f} pts)\n"
                        f"🟢 *Take Profit 1 (TP1):* {tp1} (1:{rr_1} R:R — Scale 50% & Lock BE)\n"
                        f"🎯 *Take Profit 2 (TP2):* {tp2} (1:{rr_2} R:R — Dealing Range High)\n"
                        f"🌌 *Take Profit 3 (TP3):* {tp3} (1:{rr_3} R:R — Macro Expansion Target)\n\n"
                        f"🦈 *WHALE FOOTPRINT & ORDER FLOW:*\n"
                        f"• *Lee-Ready CVD:* UNAVAILABLE (no verified order-flow feed attached to this receipt)\n"
                        f"• *Attribution tag:* {shark_tag} (UNVERIFIED USER/MODEL LABEL)\n"
                        f"• *Wyckoff Phase:* UNVERIFIED SCENARIO LABEL\n\n"
                        f"🏛️ *MODEL TRIGGER (NOT PARTICIPANT ATTRIBUTION):*\n"
                        f"• *Trigger:* {confluence_tag}\n"
                        f"• *Interpretation:* Heuristic setup label supplied by the strategy engine\n"
                        f"• *Participant identity:* UNAVAILABLE\n\n"
                        f"🌍 *MACRO & CROSS-MARKET CONTAGION:*\n"
                        f"• *Geopolitical Radar:* UNAVAILABLE IN THIS EXECUTION RECEIPT\n"
                        f"• *Cross-market contagion:* No verified live values attached\n\n"
                        f"🛡️ *RISK BUDGET & DISCIPLINE:*\n"
                        f"• *Internal pre-trade check:* Approved within configured budget\n"
                        f"• *Caution:* Stop/TP fills, breakeven outcomes, profit, and account passage are never guaranteed.\n"
                        f"• *Roman Urdu:* Broker confirmation aur spread/gap risk ko hamesha verify karein.\n\n"
                        f"💬 *1-Click Commands:* `be {symbol.lower()}` | `scale 50% {symbol.lower()}` | `close {symbol.lower()}`"
                    )

                    self.whatsapp_manager.notify_client_account_update(
                        phone=client_wa,
                        account_name=acc_name,
                        message=wa_receipt
                    )
                except Exception as e:
                    logger.warning(f"WhatsApp execution notice note: {e}")

        return {
            "success": len(executed_orders) > 0,
            "partial_success": bool(executed_orders and rejected_orders),
            "executed_count": len(executed_orders),
            "rejected_count": len(rejected_orders),
            "orders": executed_orders,
            "rejections": rejected_orders,
        }

    def _get_pip_unit(self, symbol: str) -> float:
        """Returns standard pip unit for spread buffer calculations."""
        sym = symbol.upper()
        if "XAU" in sym or "GOLD" in sym:
            return 0.1
        elif "JPY" in sym:
            return 0.01
        elif "BTC" in sym:
            return 1.0
        elif "ETH" in sym:
            return 0.1
        elif "SOL" in sym:
            return 0.01
        return 0.0001

    def manage_position_action(self, ticket, action: str, buffer_pips: float = 1.0) -> Dict[str, Any]:
        """Manage a position and mutate local state only after broker confirmation."""
        ticket_str = str(ticket)
        try:
            ticket_int = int(ticket)
        except (ValueError, TypeError):
            ticket_int = None

        valid_actions = {"be", "breakeven", "lock", "scale", "scale_50", "close", "close_all", "trail_fvg"}
        if action not in valid_actions:
            return {"success": False, "message": f"Unknown execution action '{action}'"}

        target_pos = None
        for p in self.active_positions:
            if str(p.get("ticket")) == ticket_str or (ticket_int is not None and p.get("ticket") == ticket_int):
                target_pos = p
                break

        if not target_pos:
            return {"success": False, "message": f"Position #{ticket} not found."}

        client_wa = target_pos.get("client_whatsapp", "")
        acc_name = target_pos.get("account_name", "Fleet Account")
        account_id = str(target_pos.get("account_id", ""))
        sym = target_pos.get("symbol", "EURUSD")
        pos_type = target_pos.get("type", target_pos.get("direction", "BUY")).upper()
        open_price = float(target_pos.get("open_price", 0.0))
        pip_unit = self._get_pip_unit(sym)
        is_crypto = any(k in sym for k in ["BTC", "ETH", "SOL"])
        account_connector = self.mt5_connectors.get(account_id, self.mt5_connector)

        def broker_ok(value: Any) -> bool:
            if value is True:
                return True
            if isinstance(value, dict):
                return bool(value.get("success") or value.get("status") in {"success", "FILLED", "ok"})
            return False

        if action in ["be", "breakeven", "lock"]:
            if pos_type == "BUY":
                new_sl = round(open_price + (buffer_pips * pip_unit), 5 if pip_unit < 0.01 else 2)
            else:
                new_sl = round(open_price - (buffer_pips * pip_unit), 5 if pip_unit < 0.01 else 2)
            if is_crypto:
                broker_result = self.bitget_connector.modify_position(order_id=ticket_str, new_sl=new_sl, symbol=sym)
            else:
                broker_result = account_connector.modify_position(ticket=ticket_int, new_sl=new_sl, new_tp=float(target_pos.get("tp1", 0.0))) if ticket_int is not None else False
            if not broker_ok(broker_result):
                return {"success": False, "ticket": ticket, "action": action, "message": "Broker did not confirm the stop modification; local state was unchanged."}
            target_pos["sl"] = new_sl
            target_pos["status"] = "BE_PROTECTED"
            msg = f"Ticket #{ticket} stop confirmed near breakeven ({new_sl}) with a {buffer_pips}-pip buffer. Costs, slippage, and gaps can still produce a loss."

        elif action in ["scale", "scale_50"]:
            cur_lots = float(target_pos.get("lots", 0.10))
            close_vol = round(cur_lots * 0.5, 2)
            rem_vol = max(0.01, round(cur_lots - close_vol, 2))
            if pos_type == "BUY":
                new_sl = round(open_price + (buffer_pips * pip_unit), 5 if pip_unit < 0.01 else 2)
            else:
                new_sl = round(open_price - (buffer_pips * pip_unit), 5 if pip_unit < 0.01 else 2)
            if is_crypto:
                close_result = self.bitget_connector.close_partial_position(order_id=ticket_str, close_size=close_vol, symbol=sym, side=pos_type)
                modify_result = self.bitget_connector.modify_position(order_id=ticket_str, new_sl=new_sl, symbol=sym) if broker_ok(close_result) else False
            else:
                close_result = account_connector.close_partial_position(ticket=ticket_int, close_volume=close_vol) if ticket_int is not None else False
                modify_result = account_connector.modify_position(ticket=ticket_int, new_sl=new_sl, new_tp=float(target_pos.get("tp1", 0.0))) if broker_ok(close_result) else False
            if not broker_ok(close_result):
                return {"success": False, "ticket": ticket, "action": action, "message": "Broker did not confirm the partial close; local state was unchanged."}
            target_pos["lots"] = rem_vol
            target_pos["status"] = "SCALED_50"
            if broker_ok(modify_result):
                target_pos["sl"] = new_sl
                target_pos["status"] = "SCALED_50_BE_PROTECTED"
                msg = f"Broker confirmed a {close_vol}-lot partial close and runner stop at {new_sl}."
            else:
                msg = f"Broker confirmed a {close_vol}-lot partial close, but did not confirm the runner stop update. Manual attention required."

        elif action in ["close", "close_all"]:
            if is_crypto:
                close_result = self.bitget_connector.close_position(order_id=ticket_str, symbol=sym, side=pos_type)
            else:
                close_result = account_connector.close_position(ticket=ticket_int) if ticket_int is not None else False
            if not broker_ok(close_result):
                return {"success": False, "ticket": ticket, "action": action, "message": "Broker did not confirm the close; the position remains tracked."}
            self.active_positions = [p for p in self.active_positions if str(p.get("ticket")) != ticket_str]
            self.risk_manager.release_position(account_id, ticket)
            msg = f"Broker confirmed ticket #{ticket} closed. Final P&L must be read from broker history."

        elif action in ["trail_fvg"]:
            if not self.simulation_mode:
                return {"success": False, "ticket": ticket, "action": action, "message": "Live FVG trailing requires explicit verified FVG top/bottom levels."}
            target_pos["status"] = "TRAILING_FVG"
            msg = f"Paper position #{ticket} marked for FVG trailing; no broker modification was made."

        # Notify client
        if client_wa and self.whatsapp_manager:
            try:
                self.whatsapp_manager.notify_client_account_update(
                    phone=client_wa,
                    account_name=acc_name,
                    message=f"🛡️ *TRADE UPDATE:* {msg}"
                )
            except Exception as e:
                logger.warning(f"Position action notification note: {e}")

        return {"success": True, "ticket": ticket, "action": action, "message": msg, "position": target_pos}

    def trail_fvg_consequent_encroachment(
        self,
        ticket: Any,
        fvg_top: float,
        fvg_bottom: float,
        gap_type: str = "BULLISH_BISI"
    ) -> Dict[str, Any]:
        """
        Dynamically trails Stop Loss behind the 50% Consequent Encroachment (CE) midpoint of an active FVG.
        Formula: CE = (fvg_top + fvg_bottom) / 2.0
        """
        ticket_str = str(ticket)
        try:
            ticket_int = int(ticket)
        except (ValueError, TypeError):
            ticket_int = None

        target_pos = None
        for p in self.active_positions:
            if str(p.get("ticket")) == ticket_str or (ticket_int is not None and p.get("ticket") == ticket_int):
                target_pos = p
                break

        if not target_pos:
            return {"success": False, "message": f"Position #{ticket} not found."}

        try:
            top = float(fvg_top)
            bottom = float(fvg_bottom)
        except (TypeError, ValueError):
            return {"success": False, "message": "FVG levels must be numeric"}
        if not all(math.isfinite(value) and value > 0 for value in (top, bottom)) or top <= bottom:
            return {"success": False, "message": "FVG top must be greater than a positive FVG bottom"}
        ce_50 = round((top + bottom) / 2.0, 5 if "USD" in target_pos.get("symbol", "") and "JPY" not in target_pos.get("symbol", "") else 2)

        sym = target_pos.get("symbol", "")
        account_id = str(target_pos.get("account_id", ""))
        if any(k in sym for k in ["BTC", "ETH", "SOL"]):
            broker_result = self.bitget_connector.modify_position(order_id=ticket_str, new_sl=ce_50, symbol=sym)
        else:
            connector = self.mt5_connectors.get(account_id, self.mt5_connector)
            broker_result = connector.modify_position(ticket=ticket_int, new_sl=ce_50, new_tp=float(target_pos.get("tp1", 0.0))) if ticket_int is not None else False
        confirmed = broker_result is True or (isinstance(broker_result, dict) and (broker_result.get("success") or broker_result.get("status") == "success"))
        if not confirmed:
            return {"success": False, "message": "Broker did not confirm the FVG stop modification; local state was unchanged."}
        target_pos["sl"] = ce_50
        target_pos["status"] = "TRAILING_FVG_50_CE"

        msg = f"Ticket #{ticket} SL updated to 50% FVG CE midpoint: {ce_50} (Range: {fvg_bottom} - {fvg_top})"
        logger.info(msg)
        return {
            "success": True,
            "ticket": ticket,
            "ce_50": ce_50,
            "fvg_top": fvg_top,
            "fvg_bottom": fvg_bottom,
            "gap_type": gap_type,
            "message": msg,
            "position": target_pos
        }

    def emergency_kill_switch(self) -> Dict[str, Any]:
        """
        Emergency Kill-Switch:
        Cancels all pending orders and flattens all open positions across MT5 and Bitget.
        """
        connectors = dict(self.mt5_connectors)
        connectors.setdefault("__default__", self.mt5_connector)
        unique_connectors = list({id(connector): connector for connector in connectors.values()}.values())
        mt5_closed = sum(max(0, int(connector.emergency_close_all())) for connector in unique_connectors)
        bitget_closed = self.bitget_connector.emergency_close_all()
        in_memory_closed = len(self.active_positions)
        if self.simulation_mode:
            self.active_positions.clear()
            retained = 0
            total_closed = in_memory_closed
        else:
            retained_positions = []
            for position in self.active_positions:
                account_id = str(position.get("account_id", ""))
                connector = self.mt5_connectors.get(account_id)
                if connector is None:
                    retained_positions.append(position)
                    continue
                runtime = connector.get_runtime_status()
                if not runtime.get("connected"):
                    retained_positions.append(position)
                    continue
                live_tickets = {str(item.get("ticket")) for item in connector.get_open_positions()}
                if str(position.get("ticket")) in live_tickets:
                    retained_positions.append(position)
                else:
                    self.risk_manager.release_position(account_id, position.get("ticket"))
            self.active_positions = retained_positions
            retained = len(retained_positions)
            total_closed = max(0, in_memory_closed - retained)
        success = retained == 0
        msg = f"EMERGENCY KILL SWITCH {'VERIFIED' if success else 'INCOMPLETE'}: {mt5_closed} MT5 + {bitget_closed} crypto closes reported; {retained} tracked positions require attention."
        logger.warning(msg)
        return {
            "success": success,
            "mt5_closed": mt5_closed,
            "bitget_closed": bitget_closed,
            "total_closed": total_closed,
            "unconfirmed_positions": retained,
            "status": "EMERGENCY_FLATTENED" if success else "EMERGENCY_INCOMPLETE",
            "message": msg
        }
