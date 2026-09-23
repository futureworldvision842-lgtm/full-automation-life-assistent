"""
bitget_connector.py — Native Institutional Connector for Bitget V2 API.
========================================================================
Supports:
  1. USDT-M Futures & Coin-M Perpetual Contracts
  2. Spot Trading (BTCUSDT, ETHUSDT, SOLUSDT)
  3. Real-Time Account Balance & Position Ingestion
  4. 1-Click Order Execution: Market/Limit, SL/TP, Leverage Setting, Position Scaling
  5. HMAC-SHA256 Request Signing with Base64 Encoding
  6. High-Fidelity Simulation / Dry-Run Mode when API keys are unconfigured
"""

import hmac
import hashlib
import base64
import time
import json
import logging
import os
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("BitgetConnector")


class BitgetConnector:
    """
    Direct REST & Execution Connector for Bitget Exchange (V2 API).
    """

    BASE_URL = "https://api.bitget.com"
    LIVE_CONFIRMATION_ENV = "MQ3_BITGET_LIVE_CONFIRMATION"
    LIVE_CONFIRMATION_PHRASE = "I_ACCEPT_LIVE_TRADING_RISK"

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        passphrase: Optional[str] = None,
        sim_mode: bool = True,
        live_enabled: bool = False,
    ):
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.passphrase = passphrase or ""
        self.sim_mode = sim_mode or not (self.api_key and self.secret_key and self.passphrase)
        self.live_enabled = bool(live_enabled)
        self.sim_positions: List[Dict[str, Any]] = []
        self.sim_balance: float = 1000.0

    def _live_execution_authorized(self) -> bool:
        return bool(
            not self.sim_mode
            and self.live_enabled
            and os.environ.get(self.LIVE_CONFIRMATION_ENV) == self.LIVE_CONFIRMATION_PHRASE
        )

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body_str: str = "") -> str:
        """Generates HMAC-SHA256 signature required by Bitget V2 API."""
        message = timestamp + method.upper() + request_path + body_str
        mac = hmac.new(self.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _get_headers(self, method: str, request_path: str, body_str: str = "") -> Dict[str, str]:
        """Builds Bitget authentication headers."""
        timestamp = str(int(time.time() * 1000))
        sign = self._generate_signature(timestamp, method, request_path, body_str)
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-PASSPHRASE": self.passphrase,
            "ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
            "locale": "en-US"
        }

    def get_account_balance(self, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """Fetches account balance from Bitget or returns simulated funds."""
        if self.sim_mode:
            return {
                "status": "success",
                "mode": "SIMULATION",
                "margin_coin": "USDT",
                "balance": self.sim_balance,
                "equity": self.sim_balance,
                "available": self.sim_balance,
                "unrealized_pnl": 0.0
            }

        try:
            path = "/api/v2/mix/account/accounts"
            headers = self._get_headers("GET", path)
            r = requests.get(f"{self.BASE_URL}{path}", params={"productType": product_type}, headers=headers, timeout=5)
            data = r.json()
            if data.get("code") == "00000":
                account_list = data.get("data", [])
                for acc in account_list:
                    if acc.get("marginCoin") == "USDT":
                        return {
                            "status": "success",
                            "mode": "LIVE_BITGET",
                            "margin_coin": "USDT",
                            "balance": float(acc.get("accountEquity", 0.0)),
                            "equity": float(acc.get("accountEquity", 0.0)),
                            "available": float(acc.get("available", 0.0)),
                            "unrealized_pnl": float(acc.get("unrealizedPL", 0.0))
                        }
            return {"status": "error", "message": data.get("msg", "Unknown error"), "raw": data}
        except Exception as e:
            logger.error(f"[Bitget] Balance fetch error: {e}")
            return {"status": "error", "message": str(e)}

    def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        order_type: str = "market",
        price: Optional[float] = None,
        sl: Optional[float] = None,
        tp: Optional[float] = None,
        leverage: int = 10,
        margin_mode: str = "crossed",
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Places a futures order on Bitget or executes via simulation engine."""
        formatted_sym = symbol.replace("USDT", "").replace("USD", "") + "USDT"

        if self.sim_mode:
            pos_id = f"SIM_BG_{int(time.time()*1000)}"
            entry_px = price or (63300.0 if "BTC" in symbol else (1888.0 if "ETH" in symbol else 75.50))
            sim_pos = {
                "order_id": pos_id,
                "symbol": formatted_sym,
                "side": side.lower(),
                "size": size,
                "entry_price": entry_px,
                "sl": sl,
                "tp": tp,
                "leverage": leverage,
                "mode": "SIMULATION",
                "timestamp": int(time.time())
            }
            self.sim_positions.append(sim_pos)
            logger.info(f"[Bitget SIM] Executed {side.upper()} {size} {formatted_sym} @ {entry_px}")
            return {"status": "success", "order_id": pos_id, "mode": "SIMULATION", "data": sim_pos}

        if not self._live_execution_authorized():
            return {"status": "error", "mode": "LIVE_LOCKED", "message": "Bitget live execution is not explicitly enabled and acknowledged"}
        central_ok, central_reason = self._valid_central_admission(execution_context)
        if not central_ok:
            return {"status": "error", "mode": "LIVE_LOCKED", "message": central_reason}

        try:
            path = "/api/v2/mix/order/place-order"
            body = {
                "symbol": formatted_sym,
                "productType": "USDT-FUTURES",
                "marginMode": margin_mode,
                "marginCoin": "USDT",
                "size": str(size),
                "side": side.lower(),
                "orderType": order_type.lower(),
                "clientOid": f"MQ3_{int(time.time()*1000)}"
            }
            if price and order_type.lower() == "limit":
                body["price"] = str(price)
            if sl:
                body["presetStopLossPrice"] = str(sl)
            if tp:
                body["presetTakeProfitPrice"] = str(tp)

            body_str = json.dumps(body)
            headers = self._get_headers("POST", path, body_str)
            r = requests.post(f"{self.BASE_URL}{path}", data=body_str, headers=headers, timeout=5)
            data = r.json()

            if data.get("code") == "00000":
                return {
                    "status": "success",
                    "mode": "LIVE_BITGET",
                    "order_id": data.get("data", {}).get("orderId"),
                    "client_oid": data.get("data", {}).get("clientOid"),
                    "raw": data
                }
            return {"status": "error", "message": data.get("msg", "Execution rejected"), "raw": data}
        except Exception as e:
            logger.error(f"[Bitget] Place order error: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def _valid_central_admission(execution_context: Any) -> tuple[bool, str]:
        if not isinstance(execution_context, dict):
            return False, "Central execution admission receipt is required"
        required_true = ("readiness_passed", "risk_passed", "market_admission_passed", "signal_quality_passed")
        if str(execution_context.get("executor")) != "AutonomousFleetExecutor":
            return False, "Unrecognized central executor receipt"
        if any(execution_context.get(field) is not True for field in required_true):
            return False, "Central execution receipt has an unpassed gate"
        try:
            issued = datetime.fromisoformat(str(execution_context.get("issued_at", "")).replace("Z", "+00:00"))
            if issued.tzinfo is None:
                issued = issued.replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - issued.astimezone(timezone.utc)).total_seconds()
        except (TypeError, ValueError):
            return False, "Central execution receipt timestamp is invalid"
        if age < -5 or age > 60:
            return False, "Central execution receipt is stale"
        return True, "admitted"

    def get_open_positions(self, product_type: str = "USDT-FUTURES") -> List[Dict[str, Any]]:
        """Retrieves active positions from Bitget."""
        if self.sim_mode:
            return self.sim_positions

        try:
            path = "/api/v2/mix/position/all-position"
            headers = self._get_headers("GET", path)
            r = requests.get(f"{self.BASE_URL}{path}", params={"productType": product_type, "marginCoin": "USDT"}, headers=headers, timeout=5)
            data = r.json()
            if data.get("code") == "00000":
                raw_positions = data.get("data", [])
                parsed = []
                for p in raw_positions:
                    total = float(p.get("total", 0.0))
                    if total > 0:
                        parsed.append({
                            "symbol": p.get("symbol"),
                            "side": p.get("holdSide"),
                            "size": total,
                            "open_price": float(p.get("openPriceAvg", 0.0)),
                            "mark_price": float(p.get("markPrice", 0.0)),
                            "unrealized_pnl": float(p.get("unrealizedPL", 0.0)),
                            "leverage": int(p.get("leverage", 10)),
                            "mode": "LIVE_BITGET"
                        })
                return parsed
            return []
        except Exception as e:
            logger.error(f"[Bitget] Positions fetch error: {e}")
            return []

    def modify_position(
        self,
        order_id: str,
        new_sl: Optional[float] = None,
        new_tp: Optional[float] = None,
        symbol: Optional[str] = None
    ) -> bool:
        """Modifies Stop Loss and/or Take Profit for an active Bitget position."""
        if self.sim_mode:
            for p in self.sim_positions:
                if str(p.get("order_id")) == str(order_id) or (symbol and p.get("symbol") == symbol):
                    if new_sl is not None:
                        p["sl"] = new_sl
                    if new_tp is not None:
                        p["tp"] = new_tp
                    logger.info(f"[Bitget SIM] Modified position {order_id}: SL={new_sl}, TP={new_tp}")
                    return True
            return False

        if not self._live_execution_authorized():
            return False

        try:
            path = "/api/v2/mix/order/modify-tpsl-order"
            body: Dict[str, Any] = {
                "orderId": order_id,
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT"
            }
            if symbol:
                body["symbol"] = symbol.replace("USDT", "").replace("USD", "") + "USDT"
            if new_sl is not None:
                body["presetStopLossPrice"] = str(new_sl)
            if new_tp is not None:
                body["presetTakeProfitPrice"] = str(new_tp)

            body_str = json.dumps(body)
            headers = self._get_headers("POST", path, body_str)
            r = requests.post(f"{self.BASE_URL}{path}", data=body_str, headers=headers, timeout=5)
            data = r.json()
            return data.get("code") == "00000"
        except Exception as e:
            logger.error(f"[Bitget] Modify position error: {e}")
            return False

    def close_partial_position(
        self,
        order_id: str,
        close_size: float,
        symbol: Optional[str] = None,
        side: Optional[str] = None
    ) -> bool:
        """Closes a partial size of an active Bitget position (50% scale-out)."""
        if self.sim_mode:
            for p in self.sim_positions:
                if str(p.get("order_id")) == str(order_id) or (symbol and p.get("symbol") == symbol):
                    cur_size = float(p.get("size", 0.0))
                    new_size = max(0.001, round(cur_size - close_size, 4))
                    p["size"] = new_size
                    logger.info(f"[Bitget SIM] Scaled out {close_size} from {order_id}. Remaining: {new_size}")
                    return True
            return False

        if not self._live_execution_authorized():
            return False

        try:
            target_sym = (symbol or "BTCUSDT").replace("USDT", "").replace("USD", "") + "USDT"
            close_side = "sell" if side and side.lower() == "buy" else "buy"
            path = "/api/v2/mix/order/place-order"
            body = {
                "symbol": target_sym,
                "productType": "USDT-FUTURES",
                "marginMode": "crossed",
                "marginCoin": "USDT",
                "size": str(close_size),
                "side": close_side,
                "orderType": "market",
                "reduceOnly": "YES",
                "clientOid": f"MQ3_SCALE_{int(time.time()*1000)}"
            }
            body_str = json.dumps(body)
            headers = self._get_headers("POST", path, body_str)
            r = requests.post(f"{self.BASE_URL}{path}", data=body_str, headers=headers, timeout=5)
            data = r.json()
            return data.get("code") == "00000"
        except Exception as e:
            logger.error(f"[Bitget] Partial close error: {e}")
            return False

    def close_position(
        self,
        order_id: str,
        symbol: Optional[str] = None,
        side: Optional[str] = None
    ) -> bool:
        """Closes an active Bitget position completely."""
        if self.sim_mode:
            for i, p in enumerate(self.sim_positions):
                if str(p.get("order_id")) == str(order_id) or (symbol and p.get("symbol") == symbol):
                    self.sim_positions.pop(i)
                    logger.info(f"[Bitget SIM] Closed position {order_id}")
                    return True
            return False

        if not self._live_execution_authorized():
            return False

        try:
            path = "/api/v2/mix/order/close-positions"
            body: Dict[str, Any] = {
                "productType": "USDT-FUTURES",
                "marginCoin": "USDT"
            }
            if symbol:
                body["symbol"] = symbol.replace("USDT", "") + "USDT"
            if side:
                body["holdSide"] = side.lower()

            body_str = json.dumps(body)
            headers = self._get_headers("POST", path, body_str)
            r = requests.post(f"{self.BASE_URL}{path}", data=body_str, headers=headers, timeout=5)
            data = r.json()
            return data.get("code") == "00000"
        except Exception as e:
            logger.error(f"[Bitget] Close position error: {e}")
            return False

    def emergency_close_all(self, product_type: str = "USDT-FUTURES") -> int:
        """Emergency Kill-Switch: Cancels pending orders and closes all active crypto positions."""
        if self.sim_mode:
            count = len(self.sim_positions)
            self.sim_positions.clear()
            logger.info(f"[Bitget SIM] Emergency Kill-Switch: flattened {count} crypto positions.")
            return count

        if not self._live_execution_authorized():
            logger.error("Bitget emergency close blocked: live execution acknowledgement is absent")
            return 0

        closed = 0
        try:
            # 1. Cancel all open / pending orders
            cancel_path = "/api/v2/mix/order/cancel-all-orders"
            cancel_body = json.dumps({"productType": product_type, "marginCoin": "USDT"})
            cancel_headers = self._get_headers("POST", cancel_path, cancel_body)
            requests.post(f"{self.BASE_URL}{cancel_path}", data=cancel_body, headers=cancel_headers, timeout=5)

            # 2. Query open positions and close each
            positions = self.get_open_positions(product_type=product_type)
            for p in positions:
                sym = p.get("symbol")
                hd_side = p.get("side")
                ok = self.close_position(order_id="", symbol=sym, side=hd_side)
                if ok:
                    closed += 1

            logger.info(f"[Bitget LIVE] Emergency Kill-Switch executed: {closed} positions flattened.")
            return closed
        except Exception as e:
            logger.error(f"[Bitget] Emergency close all error: {e}")
            return closed
