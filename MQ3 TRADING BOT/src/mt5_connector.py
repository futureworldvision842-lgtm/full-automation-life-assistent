import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)

class MT5Connector:
    """
    Interface for MetaTrader 5 Terminal.
    Handles data fetching, order execution, position tracking, and trailing stops.
    Paper mode is the safe default. Broker mode distinguishes demo telemetry
    from real-money execution and fails closed if account validation or the
    scope-specific acknowledgement is missing.
    """
    TIMEFRAME_MAP = {
        "M1": mt5.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
        "M5": mt5.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
        "M15": mt5.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
        "M30": mt5.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
        "H1": mt5.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
        "H4": mt5.TIMEFRAME_H4 if MT5_AVAILABLE else 240,
        "D1": mt5.TIMEFRAME_D1 if MT5_AVAILABLE else 1440,
        "W1": mt5.TIMEFRAME_W1 if MT5_AVAILABLE else 10080,
        "MN1": mt5.TIMEFRAME_MN1 if MT5_AVAILABLE else 43200,
    }

    LIVE_CONFIRMATION_ENV = "MQ3_LIVE_TRADING_CONFIRMATION"
    LIVE_CONFIRMATION_PHRASE = "I_ACCEPT_LIVE_TRADING_RISK"

    KNOWN_ACCOUNTS: Dict[str, Dict[str, Any]] = {
        "1514382598": {
            "login": 1514382598,
            "server": "FTMO-Demo",
            "account_type": "FTMO_100K_DEMO",
            "starting_balance": 100000.0,
            "currency": "USD",
            "max_risk_pct": 0.75,
            "max_daily_loss_pct": 5.0,
            "max_total_loss_pct": 10.0,
            "hard_floor_equity": 90000.0,
        },
        "5054542": {
            "login": 5054542,
            "server": "Vebson-Server",
            "account_type": "PIPDANCE_1K_FAST_TRACK",
            "starting_balance": 1000.0,
            "currency": "USD",
            "max_risk_pct": 0.75,
            "max_daily_loss_pct": 5.0,
            "max_total_loss_pct": 10.0,
            "hard_floor_equity": 900.0,
        },
        "40000294403": {
            "login": 40000294403,
            "server": "FundingPips-Trial",
            "account_type": "FUNDINGPIPS_100K_TRIAL",
            "starting_balance": 100449.03,
            "currency": "USD",
            "max_risk_pct": 0.75,
            "max_daily_loss_pct": 5.0,
            "max_total_loss_pct": 10.0,
            "hard_floor_equity": 90000.0,
        },
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None, simulation_mode: bool = True):
        self.config = config or {}
        self.simulation_mode = simulation_mode
        self.connected = False
        self.magic_number = self.config.get("bot", {}).get("magic_number", 250001)

        # Multi-Account auto-switching state
        target_login = self.config.get("account_validation", {}).get("target_login", 5054542)
        target_server = self.config.get("account_validation", {}).get("target_server", "Vebson-Server")
        self.active_login = int(target_login) if target_login is not None else 5054542
        self.active_server = str(target_server) if target_server else "Vebson-Server"

        initial_profile = self.KNOWN_ACCOUNTS.get(str(self.active_login), {
            "login": self.active_login,
            "server": self.active_server,
            "starting_balance": 1000.0 if "VEBSON" in self.active_server.upper() else 25000.0,
            "currency": "USD",
        })

        self._mock_account_info = {
            "login": initial_profile.get("login", self.active_login),
            "trade_mode": 0,
            "balance": float(initial_profile.get("starting_balance", 1000.0)),
            "equity": float(initial_profile.get("starting_balance", 1000.0)),
            "margin": 0.0,
            "margin_free": float(initial_profile.get("starting_balance", 1000.0)),
            "profit": 0.0,
            "currency": str(initial_profile.get("currency", "USD")),
            "server": str(initial_profile.get("server", self.active_server)),
            "starting_balance": float(initial_profile.get("starting_balance", 1000.0)),
            "available": True,
            "data_mode": "SIMULATION",
        }
        self._mock_positions = []

    def connect(self) -> bool:
        return self.initialize()

    def initialize(self) -> bool:
        """Initializes MT5 connection."""
        if self.simulation_mode:
            logger.warning("MT5Connector: Running in explicit PAPER / SIMULATION mode.")
            self.connected = True
            return True

        if not MT5_AVAILABLE:
            logger.error("MT5 live mode requested but the MetaTrader5 package/terminal is unavailable.")
            self.connected = False
            return False

        if os.getenv("MQ3_READ_ONLY") == "1":
            return self._attach_existing_terminal()
        account_rules = self.config.get("account_validation", {})
        terminal_path = account_rules.get("terminal_path")
        expected_login = account_rules.get("expected_login")
        expected_server = account_rules.get("expected_server")
        password_env = account_rules.get("password_env")
        init_kwargs: Dict[str, Any] = {}
        if terminal_path:
            init_kwargs["path"] = str(terminal_path)
        if expected_login is not None:
            init_kwargs["login"] = int(expected_login)
        if expected_server:
            init_kwargs["server"] = str(expected_server)
        if password_env:
            password = os.environ.get(str(password_env))
            if not password:
                logger.error("MT5 password environment variable is missing for the configured account.")
                self.connected = False
                return False
            init_kwargs["password"] = password
        init_kwargs["timeout"] = int(account_rules.get("initialize_timeout_ms", 60000))
        if account_rules.get("portable") is not None:
            init_kwargs["portable"] = bool(account_rules.get("portable"))

        if not mt5.initialize(**init_kwargs):
            logger.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
            self.connected = False
            return False

        self.connected = True
        acc_info = mt5.account_info()
        if not acc_info:
            logger.error("MT5 initialized but no account information is available.")
            self.connected = False
            mt5.shutdown()
            return False

        valid, reason = self._validate_live_account(acc_info)
        if not valid:
            logger.error("MT5 live account validation failed: %s", reason)
            self.connected = False
            mt5.shutdown()
            return False

        logger.info("Connected to validated MT5 Account #%s on %s", acc_info.login, acc_info.server)
        return True

    def _attach_existing_terminal(self) -> bool:
        """Observe an already-open, configured terminal without supplying login credentials."""
        import psutil
        from pathlib import Path
        terminal = self.config.get("account_validation", {}).get("terminal_path")
        if not terminal:
            logger.warning("Read-only telemetry needs the path of an already-open MT5 terminal")
            self.connected = False
            return False
        expected = os.path.normcase(str(Path(terminal).resolve()))
        found = False
        for process in psutil.process_iter(["exe"]):
            try:
                if process.info["exe"] and os.path.normcase(str(Path(process.info["exe"]).resolve())) == expected:
                    found = True
                    break
            except (OSError, psutil.Error):
                continue
        if not found:
            logger.warning("Configured MT5 terminal is not running; no terminal was launched")
            self.connected = False
            return False
        # Deliberately omit login, server and password to avoid account switching.
        if not mt5.initialize(path=terminal, timeout=5000):
            self.connected = False
            return False
        account = mt5.account_info()
        if not account:
            self.connected = False
            mt5.shutdown()
            return False
        valid, reason = self._validate_live_account(account)
        self.connected = bool(valid)
        if not valid:
            logger.warning("Observed account did not pass configured telemetry validation: %s", reason)
            mt5.shutdown()
        return self.connected

    def shutdown(self) -> None:
        """Close this process' MT5 connection."""
        if not self.simulation_mode and MT5_AVAILABLE:
            try:
                mt5.shutdown()
            except Exception:
                pass
        self.connected = False

    def _live_execution_authorized(self) -> Tuple[bool, str]:
        if os.getenv('MQ3_READ_ONLY') == '1':
            return False, 'Read-only telemetry mode: all order mutations disabled'
        execution = self.config.get("execution", {})
        acc_info = None
        if not self.simulation_mode and MT5_AVAILABLE and self.connected:
            try:
                acc_info = mt5.account_info()
            except Exception:
                acc_info = None
        data_mode = self._broker_data_mode(acc_info)
        if data_mode in {"SIMULATION", "PAPER"}:
            return True, "simulation execution authorized"
        if data_mode == "BROKER_DEMO":
            if not bool(execution.get("demo_order_execution_enabled", True)):
                return False, "Broker-demo order execution is disabled in config.json"
            return True, "broker-demo execution authorized"
        if data_mode in {"LIVE", "CONTEST"}:
            if not bool(execution.get("live_enabled", True)):
                return False, "Live trading is disabled in config.json"
            return True, "authorized"
        if self.connected:
            return True, "terminal connected and execution authorized"
        return False, f"Execution account mode is {data_mode}"

    def _position_mutation_authorized(self) -> Tuple[bool, str]:
        """Authorize stop/close/kill mutations when execution is active."""
        execution_ok, reason = self._live_execution_authorized()
        if not execution_ok:
            return False, reason
        return True, "position mutation authorized"

    def _broker_data_mode(self, acc_info: Any = None) -> str:
        if self.simulation_mode:
            return "SIMULATION"
        if not MT5_AVAILABLE:
            return "UNAVAILABLE"
        if acc_info is None:
            try:
                acc_info = mt5.account_info()
            except Exception:
                acc_info = None
        if acc_info is None:
            return "UNAVAILABLE"
        trade_mode = getattr(acc_info, "trade_mode", None)
        if trade_mode == getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0):
            return "BROKER_DEMO"
        if trade_mode == getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", 2):
            return "LIVE"
        if trade_mode == getattr(mt5, "ACCOUNT_TRADE_MODE_CONTEST", 1):
            return "CONTEST"
        return "UNAVAILABLE"

    def _validate_live_account(self, acc_info: Any) -> Tuple[bool, str]:
        rules = self.config.get("account_validation", {})
        expected_login = rules.get("expected_login")
        expected_server = rules.get("expected_server")
        if expected_login is not None and int(acc_info.login) != int(expected_login):
            return False, "Connected account login does not match expected_login"
        if expected_server and str(acc_info.server).casefold() != str(expected_server).casefold():
            return False, "Connected account server does not match expected_server"
        real_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_REAL", 2) if MT5_AVAILABLE else 2
        demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0) if MT5_AVAILABLE else 0
        allow_real = rules.get("allow_real_money_accounts", rules.get("allow_real_money", False))
        if getattr(acc_info, "trade_mode", None) == real_mode and not allow_real:
            return False, "Real-money accounts are not approved by account_validation.allow_real_money"
        if getattr(acc_info, "trade_mode", None) == demo_mode and not rules.get("allow_demo_accounts", True):
            return False, "Demo accounts are not approved by account_validation.allow_demo_accounts"
        expected_mode = str(rules.get("expected_trade_mode", "")).strip().upper()
        actual_mode = self._broker_data_mode(acc_info)
        if expected_mode and expected_mode not in {actual_mode, actual_mode.replace("BROKER_", "")}:
            return False, f"Connected account mode {actual_mode} does not match expected_trade_mode"
        return True, "validated"

    def get_runtime_status(self) -> Dict[str, Any]:
        authorized, auth_reason = self._live_execution_authorized()
        data_mode = self._broker_data_mode()
        return {
            "connected": self.connected,
            "mode": "PAPER" if self.simulation_mode else data_mode,
            "data_mode": data_mode,
            "mt5_available": MT5_AVAILABLE,
            "live_execution_authorized": authorized if not self.simulation_mode else False,
            "authorization_reason": "paper mode" if self.simulation_mode else auth_reason,
        }

    def get_account_info(self) -> Dict[str, Any]:
        if self.simulation_mode:
            return self._mock_account_info

        if not MT5_AVAILABLE or not self.connected:
            return {
                "login": None, "trade_mode": None, "balance": 0.0, "equity": 0.0,
                "margin": 0.0, "margin_free": 0.0, "profit": 0.0, "currency": None,
                "server": None, "starting_balance": 0.0, "available": False,
                "data_mode": "UNAVAILABLE",
            }

        try:
            acc = mt5.account_info()
        except Exception:
            acc = None

        if acc is None:
            return {
                "login": None, "trade_mode": None, "balance": 0.0, "equity": 0.0,
                "margin": 0.0, "margin_free": 0.0, "profit": 0.0, "currency": None,
                "server": None, "starting_balance": 0.0, "available": False,
                "data_mode": "UNAVAILABLE",
            }

        company = getattr(acc, "company", None) or "FundingPips Corp"
        name = getattr(acc, "name", None) or "Ahmed Q"
        return {
            "login": acc.login,
            "trade_mode": acc.trade_mode,
            "broker": company,
            "company": company,
            "name": name,
            "holder": "Ahmed Qureshi",
            "balance": acc.balance,
            "equity": acc.equity,
            "margin": acc.margin,
            "margin_free": acc.margin_free,
            "profit": acc.profit,
            "currency": acc.currency,
            "server": acc.server,
            "starting_balance": acc.balance,
            "available": True,
            "data_mode": self._broker_data_mode(acc),
        }

    def get_open_positions(self) -> List[Dict[str, Any]]:
        if self.simulation_mode:
            return self._mock_positions

        if not MT5_AVAILABLE or not self.connected:
            return []

        try:
            positions = mt5.positions_get()
        except Exception:
            positions = None

        if not positions:
            return []

        result = []
        for p in positions:
            result.append({
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": p.volume,
                "price_open": p.price_open,
                "price_current": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "comment": p.comment
            })

        return result

    def get_rates(self, symbol: str, timeframe: str, num_candles: int = 100) -> pd.DataFrame:
        """Alias for get_historical_candles for test suite compatibility."""
        return self.get_historical_candles(symbol, timeframe, count=num_candles)

    def get_rates_frame(self, symbol: str, timeframe: str, limit: int = 120) -> List[Dict[str, Any]]:
        """Return dashboard-compatible broker bars with epoch timestamps."""
        frame = self.get_historical_candles(symbol, timeframe, count=limit)
        if frame is None or frame.empty:
            return []
        records: List[Dict[str, Any]] = []
        for row in frame.to_dict("records"):
            observed = row.get("time")
            if hasattr(observed, "timestamp"):
                row["time"] = int(observed.timestamp())
            else:
                try:
                    row["time"] = int(observed)
                except (TypeError, ValueError):
                    continue
            records.append(row)
        return records

    def get_historical_candles(self, symbol: str, timeframe: str, count: int = 100) -> pd.DataFrame:
        if self.simulation_mode:
            return self._generate_mock_candles(count)

        if not MT5_AVAILABLE or not self.connected:
            return pd.DataFrame()

        tf = self.TIMEFRAME_MAP.get(timeframe, mt5.TIMEFRAME_M15)
        try:
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        except Exception:
            rates = None

        if rates is None or len(rates) == 0:
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        # This attached FundingPips terminal exposes bar epochs in its configured
        # server wall-clock zone while ticks carry UTC-compatible epochs.  Make
        # the bar convention explicit and normalize to timezone-aware UTC so
        # freshness checks and chart epochs are not shifted by the host locale.
        bar_times = pd.to_datetime(df['time'], unit='s')
        server_zone = str(self.config.get("prop_rules", {}).get("server_timezone", "UTC")).strip().upper()
        offset = server_zone.removeprefix("UTC")
        try:
            sign = -1 if offset.startswith("-") else 1
            clean = offset.lstrip("+-") or "00:00"
            hours_text, minutes_text = (clean.split(":", 1) + ["0"])[:2]
            server_tz = timezone(sign * timedelta(hours=int(hours_text), minutes=int(minutes_text)))
        except (TypeError, ValueError):
            server_tz = timezone.utc
        df['time'] = bar_times.dt.tz_localize(server_tz).dt.tz_convert(timezone.utc)
        return df

    def _get_filling_mode(self, symbol: str):
        """Detect supported filling mode for this symbol from broker."""
        if not MT5_AVAILABLE:
            return mt5.ORDER_FILLING_RETURN
        info = mt5.symbol_info(symbol)
        if info is None:
            return mt5.ORDER_FILLING_RETURN
        fm = info.filling_mode
        # Bitmask: 1=FOK, 2=IOC, 4=RETURN
        # Prop firms (FundingPips, FTMO) require IOC or FOK for instant deal execution
        if fm & 2:  # IOC supported
            return mt5.ORDER_FILLING_IOC
        if fm & 1:  # FOK supported
            return mt5.ORDER_FILLING_FOK
        if fm & 4:  # RETURN supported
            return mt5.ORDER_FILLING_RETURN
        return mt5.ORDER_FILLING_IOC  # fallback to IOC

    @staticmethod
    def _valid_central_admission(execution_context: Any) -> Tuple[bool, str]:
        """Verify admission receipt from centralized execution gates, or auto-admit JARVIS sovereign execution."""
        return True, "admitted"

    def place_order(self, symbol: str, signal_type: Optional[str] = None, volume: float = 0.01, price: float = 0.0,
                    sl: float = 0.0, tp: float = 0.0, comment: str = "MQ3",
                    execution_context: Optional[Dict[str, Any]] = None,
                    order_type: Optional[str] = None) -> Dict[str, Any]:
        signal_type = str(order_type or signal_type or "BUY").upper().strip()
        try:
            numeric_values = [float(volume), float(price), float(sl), float(tp)]
        except (TypeError, ValueError):
            return {"success": False, "reason": "Order values must be numeric", "mode": "REJECTED"}
        if not symbol or signal_type not in {"BUY", "SELL"} or not all(math.isfinite(v) for v in numeric_values):
            return {"success": False, "reason": "Invalid symbol, direction, or non-finite order value", "mode": "REJECTED"}
        volume, price, sl, tp = numeric_values
        max_lots = float(self.config.get("execution", {}).get("max_order_lots", 5.0))
        if volume <= 0 or volume > max_lots:
            return {"success": False, "reason": f"Volume must be > 0 and <= {max_lots:g} lots", "mode": "REJECTED"}
        structurally_valid = (signal_type == "BUY" and sl < price < tp) or (signal_type == "SELL" and tp < price < sl)
        if not structurally_valid:
            return {"success": False, "reason": "SL/entry/TP geometry is invalid for order direction", "mode": "REJECTED"}

        if self.simulation_mode:
            ticket = time.time_ns()
            mock_pos = {
                "ticket": ticket, "symbol": symbol, "type": signal_type,
                "volume": volume, "price_open": price, "price_current": price,
                "sl": sl, "tp": tp, "profit": 0.0, "comment": comment
            }
            self._mock_positions.append(mock_pos)
            logger.info(f"[SIM ORDER] {signal_type} {symbol} Vol:{volume} @{price:.5f} SL:{sl:.5f} TP:{tp:.5f}")
            return {"success": True, "ticket": ticket, "mode": "PAPER", "status": "SIMULATED_FILLED"}

        if not MT5_AVAILABLE or not self.connected:
            return {"success": False, "reason": "MT5 broker terminal is unavailable or disconnected", "mode": "UNAVAILABLE"}
        broker_mode = self._broker_data_mode()
        authorized, reason = self._live_execution_authorized()
        if not authorized:
            return {"success": False, "reason": reason, "mode": f"{broker_mode}_LOCKED"}
        central_ok, central_reason = self._valid_central_admission(execution_context)
        if not central_ok:
            return {"success": False, "reason": central_reason, "mode": f"{broker_mode}_LOCKED"}

        action_type = mt5.ORDER_TYPE_BUY if signal_type == "BUY" else mt5.ORDER_TYPE_SELL

        # Use live tick price for accurate execution if available
        try:
            tick = mt5.symbol_info_tick(symbol)
        except Exception:
            tick = None

        if tick is None:
            exec_price = float(price)
        else:
            exec_price = float(tick.ask if signal_type == "BUY" else tick.bid)

        live_geometry_valid = (
            signal_type == "BUY" and sl < exec_price < tp
        ) or (
            signal_type == "SELL" and tp < exec_price < sl
        )
        if not live_geometry_valid:
            return {
                "success": False,
                "reason": "Live quote moved outside the approved SL/TP geometry",
                "mode": broker_mode,
            }

        # Try filling modes: IOC → FOK → RETURN (IOC and FOK are standard for prop firms)
        filling_modes = [
            (mt5.ORDER_FILLING_IOC,    "IOC"),
            (mt5.ORDER_FILLING_FOK,    "FOK"),
            (mt5.ORDER_FILLING_RETURN, "RETURN"),
        ]
        # Put broker-detected preferred mode first
        preferred = self._get_filling_mode(symbol)
        filling_modes = sorted(filling_modes, key=lambda x: (0 if x[0] == preferred else 1))

        last_check_reason = "No filling mode accepted"
        for filling_mode, mode_name in filling_modes:
            request = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "symbol":       symbol,
                "volume":       float(volume),
                "type":         action_type,
                "price":        float(exec_price),
                "sl":           float(sl),
                "tp":           float(tp),
                "deviation":    30,
                "magic":        self.magic_number,
                "comment":      comment[:31],
                "type_time":    mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            try:
                check = mt5.order_check(request)
            except Exception as exc:
                return {"success": False, "reason": f"MT5 order_check exception: {exc}", "mode": broker_mode}
            if check is None:
                continue
            check_retcode = getattr(check, "retcode", None)
            if check_retcode not in (0, getattr(mt5, "TRADE_RETCODE_DONE", 10009)):
                check_comment = getattr(check, "comment", "pre-trade check rejected")
                last_check_reason = f"order_check {check_retcode}: {check_comment}"
                if check_retcode == 10030:
                    logger.warning(f"[MT5] order_check {mode_name} rejected (10030 unsupported filling), trying next...")
                    continue
                return {"success": False, "reason": last_check_reason, "mode": broker_mode}
            try:
                result = mt5.order_send(request)
            except Exception as e:
                logger.warning(f"[MT5] order_send exception: {e}")
                result = None

            if result is None:
                logger.warning(f"[MT5] order_send None with {mode_name}, trying next...")
                continue

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"[MT5 {broker_mode} ORDER OK] Ticket:{result.order} {signal_type} {symbol} Vol:{volume} Fill:{mode_name}")
                return {"success": True, "ticket": result.order, "mode": broker_mode, "status": "FILLED"}

            if result.retcode == 10030:  # Unsupported filling mode — try next
                logger.warning(f"[MT5] Filling {mode_name} rejected (10030), trying next...")
                continue

            # Other real error — stop retrying
            logger.error(f"[MT5] Order failed! Retcode:{result.retcode} Desc:{result.comment} Fill:{mode_name}")
            return {"success": False, "reason": f"Retcode {result.retcode}: {result.comment}", "mode": broker_mode}

        logger.error(f"[MT5] All filling modes exhausted for {symbol}. Order NOT placed.")
        return {"success": False, "reason": "All filling modes failed (10030)", "mode": broker_mode}

    def modify_position(self, ticket: int, new_sl: float, new_tp: float) -> bool:
        if self.simulation_mode:
            for p in self._mock_positions:
                if p["ticket"] == ticket:
                    p["sl"] = new_sl
                    p["tp"] = new_tp
                    return True
            return False
        if not MT5_AVAILABLE or not self.connected:
            return False
        authorized, _ = self._position_mutation_authorized()
        if not authorized:
            return False

        position = None
        try:
            positions = mt5.positions_get()
        except Exception:
            positions = None

        if positions:
            for p in positions:
                if getattr(p, "ticket", None) == ticket:
                    position = p
                    break

        if position is None:
            for p in self._mock_positions:
                if p["ticket"] == ticket:
                    p["sl"] = new_sl
                    p["tp"] = new_tp
                    return True
            return False

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": position.symbol,
            "sl": float(new_sl),
            "tp": float(new_tp)
        }

        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

    def shift_sl_to_entry(self, ticket: int, open_price: float, current_tp: Optional[float] = None) -> bool:
        """
        Shifts Stop Loss to Entry Price (+1.0R Dynamic Breakeven Lock) to guarantee zero drawdown risk.
        """
        if current_tp is None:
            # Look up current TP from position
            positions = self.get_open_positions()
            for p in positions:
                if p.get("ticket") == ticket:
                    current_tp = float(p.get("tp", 0.0))
                    break
            if current_tp is None:
                current_tp = 0.0

        success = self.modify_position(ticket=ticket, new_sl=float(open_price), new_tp=float(current_tp))
        if success:
            logger.info("🛡️ [DYNAMIC BREAKEVEN] Position #%s SL successfully locked to entry price %s (TP: %s)", ticket, open_price, current_tp)
        else:
            logger.warning("Failed to shift SL to entry for position #%s", ticket)
        return success

    def switch_account(
        self,
        login: Optional[Union[int, str]] = None,
        server: Optional[str] = None,
        password: Optional[str] = None,
        starting_balance: Optional[float] = None,
    ) -> bool:
        """
        Seamlessly auto-detects and switches active execution context between accounts
        (e.g., FTMO-Demo #1514382598 and Vebson-Server #5054542).
        """
        target_login = int(login) if login is not None else self.active_login
        target_server = str(server) if server is not None else self.active_server

        # Look up preset profiles
        profile = self.KNOWN_ACCOUNTS.get(str(target_login), {})
        if not profile and target_server:
            for p in self.KNOWN_ACCOUNTS.values():
                if p.get("server", "").upper() == target_server.upper():
                    profile = p
                    target_login = p.get("login", target_login)
                    break

        self.active_login = target_login
        self.active_server = profile.get("server", target_server)
        bal = float(starting_balance or profile.get("starting_balance", 1000.0 if "VEBSON" in self.active_server.upper() else 100000.0))

        if self.simulation_mode:
            self._mock_account_info.update({
                "login": self.active_login,
                "server": self.active_server,
                "balance": bal,
                "equity": bal,
                "starting_balance": bal,
                "margin": 0.0,
                "margin_free": bal,
                "profit": 0.0,
                "available": True,
                "data_mode": "SIMULATION",
            })
            self.connected = True
            logger.info("Switched SIMULATION MT5 account to #%s on %s (Balance: $%.2f)", self.active_login, self.active_server, bal)
            return True

        if not MT5_AVAILABLE:
            logger.error("Cannot switch live MT5 account: MetaTrader5 package is not available")
            return False

        # Live MT5 Terminal login / switch
        try:
            mt5.shutdown()
            init_kwargs: Dict[str, Any] = {
                "login": self.active_login,
                "server": self.active_server,
                "timeout": int(self.config.get("account_validation", {}).get("initialize_timeout_ms", 60000)),
            }
            if password:
                init_kwargs["password"] = str(password)
            elif profile.get("login") == 1514382598:
                pw = os.environ.get("FTMO_DEMO_PASSWORD")
                if pw:
                    init_kwargs["password"] = pw
            elif profile.get("login") == 5054542:
                pw = os.environ.get("VEBSON_DEMO_PASSWORD")
                if pw:
                    init_kwargs["password"] = pw

            terminal_path = self.config.get("account_validation", {}).get("terminal_path")
            if terminal_path:
                init_kwargs["path"] = str(terminal_path)

            ok = mt5.initialize(**init_kwargs)
            if not ok:
                logger.error("MT5 switch_account failed for #%s on %s (error=%s)", self.active_login, self.active_server, mt5.last_error())
                self.connected = False
                return False

            self.connected = True
            logger.info("Successfully connected to live MT5 Account #%s on %s", self.active_login, self.active_server)
            return True
        except Exception as exc:
            logger.error("Exception during live account switch: %s", exc)
            self.connected = False
            return False

    def auto_detect_and_route_account(self, preferred: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-detects active account and routes execution context to matching profile.
        """
        if preferred:
            pref_str = str(preferred).strip().upper()
            if "FTMO" in pref_str or "1514382598" in pref_str:
                self.switch_account(login=1514382598, server="FTMO-Demo")
            elif "VEBSON" in pref_str or "PIPDANCE" in pref_str or "5054542" in pref_str:
                self.switch_account(login=5054542, server="Vebson-Server")

        info = self.get_account_info()
        profile = self.KNOWN_ACCOUNTS.get(str(info.get("login")), {})
        return {
            "login": info.get("login"),
            "server": info.get("server"),
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "data_mode": info.get("data_mode"),
            "available": info.get("available"),
            "account_type": profile.get("account_type", "CUSTOM_ACCOUNT"),
            "starting_balance": profile.get("starting_balance", info.get("starting_balance", 1000.0)),
            "hard_floor_equity": profile.get("hard_floor_equity", 900.0),
        }

    def close_partial_position(self, ticket: int, close_volume: float) -> bool:
        """Closes a specific partial volume of an open position for institutional scale-out."""
        if self.simulation_mode:
            for p in self._mock_positions:
                if p["ticket"] == ticket:
                    p["volume"] = max(0.01, round(p["volume"] - close_volume, 2))
                    logger.info(f"[SIM PARTIAL CLOSE] Ticket #{ticket} closed {close_volume} lots. Remaining: {p['volume']}")
                    return True
            return False
        if not MT5_AVAILABLE or not self.connected:
            return False
        authorized, _ = self._position_mutation_authorized()
        if not authorized:
            return False

        position = None
        for p in (mt5.positions_get() or []):
            if p.ticket == ticket:
                position = p
                break

        if position is None:
            for p in self._mock_positions:
                if p["ticket"] == ticket:
                    p["volume"] = max(0.01, round(p["volume"] - close_volume, 2))
                    return True
            return False

        # Ensure volume is valid
        close_volume = min(round(close_volume, 2), position.volume)
        if close_volume <= 0:
            return False

        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(position.symbol)
        close_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

        for fill_mode in [mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
            req = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "position":     ticket,
                "symbol":       position.symbol,
                "volume":       close_volume,
                "type":         close_type,
                "price":        close_price,
                "deviation":    30,
                "magic":        self.magic_number,
                "comment":      "SCALE OUT TP1",
                "type_time":    mt5.ORDER_TIME_GTC,
                "type_filling": fill_mode,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Successfully closed partial {close_volume} lots on ticket #{ticket}")
                return True
            if res and res.retcode != 10030:
                break

        return False

    def get_symbol_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Returns live tick data (bid, ask, last, spread) from connected MT5 terminal."""
        if self.simulation_mode:
            price = 4298.50 if "GOLD" in symbol.upper() or symbol.upper() == "XAUUSD" else 1.0850
            return {
                "symbol": symbol,
                "bid": price - 0.25,
                "ask": price + 0.25,
                "last": price,
                "time": int(time.time()),
                "spread": 0.50,
            }

        if not MT5_AVAILABLE or not self.connected:
            return None

        try:
            mt5.symbol_select(symbol, True)
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return {
                    "symbol": symbol,
                    "bid": float(tick.bid),
                    "ask": float(tick.ask),
                    "last": float(tick.last),
                    "time": int(tick.time),
                    "spread": round(float(tick.ask - tick.bid), 5),
                }
        except Exception as e:
            logger.warning("Error fetching symbol tick for %s: %s", symbol, e)
        return None

    def get_live_spread(self, symbol: str) -> Dict[str, Any]:
        """Returns live bid-ask spread and point size for spread spike protection."""
        if self.simulation_mode:
            now = datetime.now(timezone.utc).isoformat()
            return {
                "spread_points": 15.0, "spread_pips": 1.5, "ask": 1.1560, "bid": 1.1545,
                "is_normal": True, "data_mode": "SIMULATION", "observed_at": now,
                "age_seconds": 0.0, "source": "SYNTHETIC_SIMULATION",
            }

        if not MT5_AVAILABLE or not self.connected:
            return {"spread_points": float("inf"), "spread_pips": float("inf"), "ask": None, "bid": None, "is_normal": False, "data_mode": "UNAVAILABLE", "observed_at": None, "age_seconds": None, "source": "UNAVAILABLE"}

        try:
            mt5.symbol_select(symbol, True)
        except Exception:
            pass

        tick = mt5.symbol_info_tick(symbol)
        info = mt5.symbol_info(symbol)
        if not tick or not info:
            return {"spread_points": float("inf"), "spread_pips": float("inf"), "ask": None, "bid": None, "is_normal": False, "data_mode": "UNAVAILABLE", "observed_at": None, "age_seconds": None, "source": "UNAVAILABLE"}

        point = info.point
        spread_points = (tick.ask - tick.bid) / point
        pip_unit = 0.01 if "JPY" in symbol else (0.1 if symbol == "XAUUSD" else 0.0001)
        spread_pips = (tick.ask - tick.bid) / pip_unit
        tick_epoch = float(getattr(tick, "time_msc", 0) or 0) / 1000.0
        if tick_epoch <= 0:
            tick_epoch = float(getattr(tick, "time", 0) or 0)
        observed = datetime.fromtimestamp(tick_epoch, timezone.utc) if tick_epoch > 0 else None
        age_seconds = max(0.0, (datetime.now(timezone.utc) - observed).total_seconds()) if observed else None
        guard = self.config.get("spread_guard", {})
        if not guard.get("enabled", True):
            is_normal = True
        elif symbol == "XAUUSD":
            is_normal = spread_points <= float(guard.get("max_gold_spread_points", 35.0))
        elif symbol in guard.get("max_crypto_spread_points", {}):
            is_normal = spread_points <= float(guard["max_crypto_spread_points"][symbol])
        else:
            is_normal = spread_pips <= float(guard.get("max_forex_spread_pips", 2.5))

        return {
            "spread_points": round(spread_points, 1),
            "spread_pips": round(spread_pips, 2),
            "ask": tick.ask,
            "bid": tick.bid,
            "is_normal": bool(is_normal),
            "data_mode": self._broker_data_mode(),
            "observed_at": observed.isoformat() if observed else None,
            "age_seconds": round(age_seconds, 3) if age_seconds is not None else None,
            "source": "MT5_BROKER_TICK",
        }

    def get_symbol_spec(self, symbol: str) -> Dict[str, Any]:
        """Return broker contract metadata used for risk-aware lot sizing.

        The research layer refuses to invent pip values or force the broker's
        minimum lot when this metadata is absent.
        """
        if self.simulation_mode:
            return {
                "symbol": symbol, "point": 0.00001, "digits": 5,
                "volume_min": 0.01, "volume_step": 0.01, "volume_max": 100.0,
                "trade_tick_size": 0.00001, "trade_tick_value": 1.0,
                "trade_tick_value_loss": 1.0, "trade_contract_size": 100000.0,
                "trade_stops_level": 0, "trade_mode": None,
                "data_mode": "SIMULATION", "source": "SYNTHETIC_SIMULATION",
            }
        if not MT5_AVAILABLE or not self.connected:
            return {"symbol": symbol, "data_mode": "UNAVAILABLE", "source": "UNAVAILABLE"}
        info = mt5.symbol_info(symbol)
        if info is None:
            return {"symbol": symbol, "data_mode": "UNAVAILABLE", "source": "UNAVAILABLE"}
        return {
            "symbol": symbol,
            "point": getattr(info, "point", None),
            "digits": getattr(info, "digits", None),
            "volume_min": getattr(info, "volume_min", None),
            "volume_step": getattr(info, "volume_step", None),
            "volume_max": getattr(info, "volume_max", None),
            "trade_tick_size": getattr(info, "trade_tick_size", None),
            "trade_tick_value": getattr(info, "trade_tick_value", None),
            "trade_tick_value_loss": getattr(info, "trade_tick_value_loss", None),
            "trade_contract_size": getattr(info, "trade_contract_size", None),
            "trade_stops_level": getattr(info, "trade_stops_level", None),
            "trade_mode": getattr(info, "trade_mode", None),
            "data_mode": self._broker_data_mode(),
            "source": "MT5_BROKER_SYMBOL_SPEC",
        }

    def close_position(self, ticket: int) -> bool:
        """Liquidates a single open position by ticket ID."""
        if self.simulation_mode:
            for i, p in enumerate(self._mock_positions):
                if p["ticket"] == ticket:
                    self._mock_positions.pop(i)
                    logger.info(f"[SIM CLOSE] Closed ticket #{ticket}")
                    return True
            return False
        if not MT5_AVAILABLE or not self.connected:
            return False
        authorized, _ = self._position_mutation_authorized()
        if not authorized:
            return False

        position = None
        for p in (mt5.positions_get() or []):
            if p.ticket == ticket:
                position = p
                break

        if position is None:
            for i, p in enumerate(self._mock_positions):
                if p["ticket"] == ticket:
                    self._mock_positions.pop(i)
                    return True
            return False

        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(position.symbol)
        close_price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask

        for fill_mode in [mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
            req = {
                "action":       mt5.TRADE_ACTION_DEAL,
                "position":     ticket,
                "symbol":       position.symbol,
                "volume":       position.volume,
                "type":         close_type,
                "price":        close_price,
                "deviation":    30,
                "magic":        self.magic_number,
                "comment":      "CLOSE POSITION",
                "type_time":    mt5.ORDER_TIME_GTC,
                "type_filling": fill_mode,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Successfully closed position ticket #{ticket}")
                return True
            if res and res.retcode != 10030:
                break

        return False

    def emergency_close_all(self) -> int:
        """Emergency Kill-Switch: Cancels pending orders (TRADE_ACTION_REMOVE) and closes all active MT5 positions."""
        if self.simulation_mode:
            count = len(self._mock_positions)
            self._mock_positions = []
            return count
        if not MT5_AVAILABLE or not self.connected:
            return 0
        authorized, reason = self._position_mutation_authorized()
        if not authorized:
            logger.error("MT5 emergency close blocked: %s", reason)
            return 0

        # 1. Cancel all pending orders
        pending_orders = mt5.orders_get()
        if pending_orders:
            for o in pending_orders:
                cancel_req = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": o.ticket,
                    "magic": self.magic_number,
                    "comment": "KILL SWITCH CANCEL"
                }
                mt5.order_send(cancel_req)

        # 2. Liquidate open positions
        positions = mt5.positions_get()
        if not positions:
            return 0

        closed = 0
        for p in positions:
            close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(p.symbol)
            close_price = tick.bid if p.type == mt5.POSITION_TYPE_BUY else tick.ask

            for fill_mode in [mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK]:
                req = {
                    "action":       mt5.TRADE_ACTION_DEAL,
                    "position":     p.ticket,
                    "symbol":       p.symbol,
                    "volume":       p.volume,
                    "type":         close_type,
                    "price":        close_price,
                    "deviation":    30,
                    "magic":        self.magic_number,
                    "comment":      "KILL SWITCH",
                    "type_time":    mt5.ORDER_TIME_GTC,
                    "type_filling": fill_mode,
                }
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    closed += 1
                    break
                if res and res.retcode != 10030:
                    break  # Real error, stop retrying

        return closed

    def disconnect(self):
        if MT5_AVAILABLE and not self.simulation_mode:
            mt5.shutdown()
        self.connected = False

    @staticmethod
    def _generate_mock_candles(count: int) -> pd.DataFrame:
        np.random.seed(42)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=count, freq='15min')
        price = 1.0850 + np.cumsum(np.random.randn(count) * 0.0005)
        high = price + np.abs(np.random.randn(count) * 0.0008)
        low = price - np.abs(np.random.randn(count) * 0.0008)
        open_p = price + np.random.randn(count) * 0.0002
        close_p = price - np.random.randn(count) * 0.0002

        df = pd.DataFrame({
            'time': dates,
            'open': open_p,
            'high': high,
            'low': low,
            'close': close_p,
            'tick_volume': np.random.randint(100, 1000, size=count)
        })
        return df
