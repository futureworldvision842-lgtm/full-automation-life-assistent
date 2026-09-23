"""
Multi-Broker Bridge Module
Extracted from digistoremaster/metatrader-to-ibkr-tws-api-bridge architecture.
Provides abstract BrokerBridge, IBKR-specific connector, and Trade Replicator
for future multi-broker position synchronisation.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Ensure event loop exists before importing ib_insync (Python 3.10+)
try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Optional IBKR import
try:
    from ib_insync import IB, Forex, MarketOrder, StopOrder, LimitOrder, Contract
    IBKR_AVAILABLE = True
except (ImportError, Exception):
    IBKR_AVAILABLE = False


# ---------------------------------------------------------------------------
# 1. Abstract Broker Bridge
# ---------------------------------------------------------------------------

class BrokerBridge:
    """
    Abstract bridge pattern for replicating MT5 trades to external brokers.
    Handles symbol mapping, lot scaling, position sync, and bracket orders.
    """

    def __init__(self, name: str = "GenericBridge"):
        self.name = name
        self.symbol_map: Dict[str, Dict[str, str]] = {}
        self._connected = False
        logger.info(f"BrokerBridge [{self.name}] initialized.")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def map_symbol(self, mt5_symbol: str) -> Dict[str, str]:
        """Map MT5 symbol to broker-specific contract identifier."""
        mapped = self.symbol_map.get(mt5_symbol)
        if mapped:
            return mapped
        # Default passthrough
        return {"symbol": mt5_symbol, "exchange": "SMART", "secType": "CASH", "currency": "USD"}

    def calculate_bridge_lot_size(
        self,
        mt5_volume: float,
        sizing_mode: str = "mirror",
        mt5_equity: float = 25000.0,
        broker_equity: float = 25000.0,
        multiplier: float = 1.0,
        fixed_lots: float = 0.01,
    ) -> float:
        """
        Calculate lot size for broker order based on sizing mode.

        Modes:
            mirror       – exact copy of MT5 volume
            multiplier   – MT5 volume × multiplier factor
            equity_ratio – scale by broker_equity / mt5_equity
            fixed        – fixed lot size regardless of MT5
        """
        if sizing_mode == "mirror":
            result = mt5_volume
        elif sizing_mode == "multiplier":
            result = mt5_volume * multiplier
        elif sizing_mode == "equity_ratio":
            ratio = broker_equity / max(mt5_equity, 1.0)
            result = mt5_volume * ratio
        elif sizing_mode == "fixed":
            result = fixed_lots
        else:
            result = mt5_volume

        result = round(max(result, 0.01), 2)
        logger.info(f"[Bridge Lot] Mode={sizing_mode} | MT5={mt5_volume} => Broker={result}")
        return result

    def sync_positions(
        self,
        mt5_positions: List[Dict[str, Any]],
        broker_positions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Compare MT5 and broker positions, return list of sync actions.
        Actions: OPEN, CLOSE, MODIFY_SL, MODIFY_TP
        """
        actions: List[Dict[str, Any]] = []

        mt5_tickets = {p.get("symbol", ""): p for p in mt5_positions}
        broker_tickets = {p.get("symbol", ""): p for p in broker_positions}

        # Positions in MT5 but not in broker → OPEN
        for sym, mt5_pos in mt5_tickets.items():
            mapped_sym = self.map_symbol(sym).get("symbol", sym)
            if mapped_sym not in broker_tickets:
                actions.append({
                    "action": "OPEN",
                    "symbol": sym,
                    "mapped_symbol": mapped_sym,
                    "direction": mt5_pos.get("type", "BUY"),
                    "volume": mt5_pos.get("volume", 0.01),
                    "sl": mt5_pos.get("sl"),
                    "tp": mt5_pos.get("tp"),
                })

        # Positions in broker but not in MT5 → CLOSE
        for sym, br_pos in broker_tickets.items():
            reverse_map = {v.get("symbol", ""): k for k, v in self.symbol_map.items()}
            mt5_sym = reverse_map.get(sym, sym)
            if mt5_sym not in mt5_tickets:
                actions.append({
                    "action": "CLOSE",
                    "symbol": sym,
                    "broker_position": br_pos,
                })

        # Both exist → check SL/TP modifications
        for sym, mt5_pos in mt5_tickets.items():
            mapped_sym = self.map_symbol(sym).get("symbol", sym)
            if mapped_sym in broker_tickets:
                br_pos = broker_tickets[mapped_sym]
                if mt5_pos.get("sl") != br_pos.get("sl"):
                    actions.append({
                        "action": "MODIFY_SL",
                        "symbol": mapped_sym,
                        "new_sl": mt5_pos.get("sl"),
                    })
                if mt5_pos.get("tp") != br_pos.get("tp"):
                    actions.append({
                        "action": "MODIFY_TP",
                        "symbol": mapped_sym,
                        "new_tp": mt5_pos.get("tp"),
                    })

        if actions:
            logger.info(f"[Position Sync] {len(actions)} actions needed: {[a['action'] for a in actions]}")
        return actions

    def generate_bracket_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Create parent + SL + TP bracket order structure."""
        direction = signal.get("direction", "BUY")
        volume = signal.get("lot_size", 0.01)
        entry = signal.get("entry_price", 0.0)
        sl = signal.get("sl", 0.0)
        tp = signal.get("tp", 0.0)

        bracket = {
            "parent_order": {
                "action": direction,
                "order_type": "MARKET",
                "quantity": volume,
                "entry_price": entry,
            },
            "stop_loss_order": {
                "action": "SELL" if direction == "BUY" else "BUY",
                "order_type": "STOP",
                "quantity": volume,
                "trigger_price": sl,
            },
            "take_profit_order": {
                "action": "SELL" if direction == "BUY" else "BUY",
                "order_type": "LIMIT",
                "quantity": volume,
                "limit_price": tp,
            },
        }
        logger.info(f"[Bracket Order] {direction} {volume} lots | SL={sl} | TP={tp}")
        return bracket


# ---------------------------------------------------------------------------
# 2. IBKR Bridge Connector  (Interactive Brokers specific)
# ---------------------------------------------------------------------------

class IBKRBridgeConnector(BrokerBridge):
    """
    Interactive Brokers TWS API bridge connector.
    Extends BrokerBridge with IBKR-specific symbol mappings and
    ib_insync connection management.
    """

    DEFAULT_SYMBOL_MAP = {
        "EURUSD": {"symbol": "EUR", "currency": "USD", "secType": "CASH", "exchange": "IDEALPRO"},
        "GBPUSD": {"symbol": "GBP", "currency": "USD", "secType": "CASH", "exchange": "IDEALPRO"},
        "USDJPY": {"symbol": "USD", "currency": "JPY", "secType": "CASH", "exchange": "IDEALPRO"},
        "XAUUSD": {"symbol": "GC", "currency": "USD", "secType": "FUT", "exchange": "COMEX"},
        "US30":   {"symbol": "YM", "currency": "USD", "secType": "FUT", "exchange": "CBOT"},
        "US500":  {"symbol": "ES", "currency": "USD", "secType": "FUT", "exchange": "CME"},
        "DE40":   {"symbol": "DAX", "currency": "EUR", "secType": "CFD", "exchange": "SMART"},
    }

    def __init__(self):
        super().__init__(name="IBKR-TWS-Bridge")
        self.symbol_map = dict(self.DEFAULT_SYMBOL_MAP)
        self.ib = None
        self.host = "127.0.0.1"
        self.port = 7497  # Paper trading default
        self.client_id = 1
        logger.info(f"IBKRBridgeConnector ready (ib_insync available: {IBKR_AVAILABLE}).")

    def connect(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1) -> bool:
        """Connect to Interactive Brokers TWS / IB Gateway."""
        self.host = host
        self.port = port
        self.client_id = client_id

        if not IBKR_AVAILABLE:
            logger.warning("ib_insync not installed — IBKR bridge in simulation mode.")
            self._connected = False
            return False

        try:
            self.ib = IB()
            self.ib.connect(host, port, clientId=client_id, timeout=10)
            self._connected = self.ib.isConnected()
            if self._connected:
                logger.info(f"Connected to IBKR TWS at {host}:{port}")
            return self._connected
        except Exception as e:
            logger.warning(f"IBKR connection failed: {e}")
            self._connected = False
            return False

    def get_ibkr_positions(self) -> List[Dict[str, Any]]:
        """Fetch current IBKR positions."""
        if not IBKR_AVAILABLE or not self._connected or self.ib is None:
            return []

        try:
            positions = self.ib.positions()
            return [
                {
                    "symbol": p.contract.symbol,
                    "exchange": p.contract.exchange,
                    "volume": float(p.position),
                    "avg_cost": float(p.avgCost),
                }
                for p in positions
            ]
        except Exception as e:
            logger.warning(f"IBKR position fetch failed: {e}")
            return []

    def disconnect(self) -> None:
        """Disconnect from IBKR."""
        if self.ib and self._connected:
            try:
                self.ib.disconnect()
            except Exception:
                pass
        self._connected = False
        logger.info("IBKR disconnected.")


# ---------------------------------------------------------------------------
# 3. Trade Replicator  (position sync engine)
# ---------------------------------------------------------------------------

class TradeReplicator:
    """
    Converts MT5 trade signals into broker order dicts and manages
    cross-broker position synchronisation with slippage guards.
    """

    def __init__(self, bridge: Optional[BrokerBridge] = None):
        self.bridge = bridge or BrokerBridge()
        self.replicated_trades: List[Dict[str, Any]] = []
        self.sync_log: List[Dict[str, Any]] = []
        logger.info(f"TradeReplicator initialized with bridge: {self.bridge.name}")

    def replicate_mt5_trade(self, mt5_trade: Dict[str, Any]) -> Dict[str, Any]:
        """Convert an MT5 trade dict into a broker-formatted order dict."""
        symbol = mt5_trade.get("symbol", "EURUSD")
        mapped = self.bridge.map_symbol(symbol)

        broker_order = {
            "mapped_symbol": mapped,
            "direction": mt5_trade.get("type", "BUY"),
            "volume": self.bridge.calculate_bridge_lot_size(
                mt5_trade.get("volume", 0.01),
                sizing_mode="mirror",
            ),
            "entry_price": mt5_trade.get("price_open", 0.0),
            "sl": mt5_trade.get("sl", 0.0),
            "tp": mt5_trade.get("tp", 0.0),
            "bracket": self.bridge.generate_bracket_order(mt5_trade),
            "replicated_at": datetime.now(timezone.utc).isoformat(),
            "source_ticket": mt5_trade.get("ticket", 0),
        }

        self.replicated_trades.append(broker_order)
        logger.info(f"[Replicated] MT5 #{mt5_trade.get('ticket', '?')} => {mapped.get('symbol', symbol)}")
        return broker_order

    @staticmethod
    def check_slippage(mt5_price: float, broker_price: float, max_slippage_pips: float = 3.0,
                       pip_unit: float = 0.0001) -> bool:
        """Check if cross-broker price slippage is within acceptable range."""
        slippage_pips = abs(mt5_price - broker_price) / pip_unit
        acceptable = slippage_pips <= max_slippage_pips
        if not acceptable:
            logger.warning(
                f"[Slippage Guard] {slippage_pips:.1f} pips exceeds max {max_slippage_pips} — order blocked!"
            )
        return acceptable

    def get_sync_status(self) -> Dict[str, Any]:
        """Return summary of replicated and sync state."""
        return {
            "bridge_name": self.bridge.name,
            "bridge_connected": self.bridge.is_connected,
            "total_replicated": len(self.replicated_trades),
            "sync_actions_pending": len(self.sync_log),
            "last_replicated": (
                self.replicated_trades[-1].get("replicated_at")
                if self.replicated_trades else None
            ),
        }


# ---------------------------------------------------------------------------
# 4. Bitget Bridge Connector & Dual-Venue Router Bridge
# ---------------------------------------------------------------------------

class BitgetBridgeConnector(BrokerBridge):
    """
    Bitget V2 API Bridge Connector.
    Maps Crypto pairs (BTCUSD, ETHUSD, SOLUSD) to Bitget USDT-M perpetuals
    and dispatches execution directly via BitgetConnector.
    """
    DEFAULT_SYMBOL_MAP = {
        "BTCUSD": {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
        "ETHUSD": {"symbol": "ETHUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
        "SOLUSD": {"symbol": "SOLUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
        "BTCUSDT": {"symbol": "BTCUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
        "ETHUSDT": {"symbol": "ETHUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
        "SOLUSDT": {"symbol": "SOLUSDT", "productType": "USDT-FUTURES", "secType": "CRYPTO_FUT"},
    }

    def __init__(self, bitget_connector: Optional[Any] = None):
        super().__init__(name="Bitget-V2-Bridge")
        self.symbol_map = dict(self.DEFAULT_SYMBOL_MAP)
        if bitget_connector is not None:
            self.connector = bitget_connector
        else:
            from src.bitget_connector import BitgetConnector
            self.connector = BitgetConnector()
        self._connected = True

    def place_bridge_order(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an order to Bitget via the underlying connector."""
        sym = signal.get("symbol", "BTCUSD")
        mapped = self.map_symbol(sym)
        target_sym = mapped.get("symbol", sym)
        side = signal.get("direction", signal.get("type", "BUY")).lower()
        size = self.calculate_bridge_lot_size(signal.get("volume", signal.get("lots", 0.01)))
        price = signal.get("entry_price", signal.get("price"))
        sl = signal.get("sl")
        tp = signal.get("tp")

        return self.connector.place_order(
            symbol=target_sym,
            side=side,
            size=size,
            order_type="market" if not price else "limit",
            price=price,
            sl=sl,
            tp=tp
        )


class DualVenueRouterBridge:
    """
    Unified Dual-Venue Router Bridge:
    Directs Forex and Commodities to MT5 and Crypto to Bitget with cross-venue
    lot calibration, bracket order management, and position synchronization.
    """
    def __init__(
        self,
        mt5_bridge: Optional[BrokerBridge] = None,
        bitget_bridge: Optional[BitgetBridgeConnector] = None
    ):
        self.mt5_bridge = mt5_bridge or BrokerBridge(name="MT5-Forex-Bridge")
        self.bitget_bridge = bitget_bridge or BitgetBridgeConnector()

    def route(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Routes order to MT5 or Bitget depending on symbol taxonomy."""
        sym = order.get("symbol", "EURUSD").upper()
        if any(c in sym for c in ["BTC", "ETH", "SOL", "USDT"]):
            mapped = self.bitget_bridge.map_symbol(sym)
            res = self.bitget_bridge.place_bridge_order(order)
            return {
                "venue": "BITGET",
                "symbol": sym,
                "target_symbol": mapped.get("symbol", sym),
                "result": res
            }
        else:
            mapped = self.mt5_bridge.map_symbol(sym)
            return {
                "venue": "MT5",
                "symbol": sym,
                "target_symbol": mapped.get("symbol", sym),
                "bracket": self.mt5_bridge.generate_bracket_order(order)
            }

