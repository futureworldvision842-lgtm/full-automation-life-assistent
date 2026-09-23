"""Isolated MetaTrader terminal workers for a multi-account fleet.

The MetaTrader5 Python package maintains process-global terminal state.  Each
funded account is therefore hosted in its own spawned worker process and exposed
through this small connector-compatible proxy.  No credentials are written to
the fleet manifest; the underlying connector reads the configured password
environment variable inside the worker.
"""

from __future__ import annotations

import multiprocessing
from multiprocessing.connection import Connection
import threading
import time
import uuid
from typing import Any, Dict, List, Optional


def _worker_main(pipe: Connection, connector_config: Dict[str, Any], simulation_mode: bool) -> None:
    from src.mt5_connector import MT5Connector

    connector = MT5Connector(config=connector_config, simulation_mode=simulation_mode)
    connected = connector.connect()
    pipe.send({
        "type": "READY",
        "connected": connected,
        "runtime_status": connector.get_runtime_status(),
        "account_info": connector.get_account_info(),
    })
    while True:
        try:
            message = pipe.recv()
        except EOFError:
            break
        request_id = message.get("request_id")
        command = message.get("command")
        kwargs = message.get("kwargs", {})
        try:
            if command == "shutdown":
                connector.shutdown()
                pipe.send({"request_id": request_id, "success": True})
                break
            if command == "get_runtime_status":
                result = connector.get_runtime_status()
            elif command == "get_account_info":
                result = connector.get_account_info()
            elif command == "get_open_positions":
                result = connector.get_open_positions()
            elif command == "place_order":
                result = connector.place_order(**kwargs)
            elif command == "modify_position":
                result = connector.modify_position(**kwargs)
            elif command == "close_position":
                result = connector.close_position(**kwargs)
            elif command == "close_partial_position":
                result = connector.close_partial_position(**kwargs)
            elif command == "emergency_close_all":
                result = connector.emergency_close_all()
            else:
                raise ValueError(f"Unsupported worker command: {command}")
            pipe.send({"request_id": request_id, "success": True, "result": result})
        except Exception as exc:
            pipe.send({"request_id": request_id, "success": False, "error": f"{type(exc).__name__}: {exc}"})


class MT5TerminalWorkerProxy:
    """Connector-compatible proxy for one account-specific MT5 process."""

    def __init__(
        self,
        *,
        account_id: Any,
        connector_config: Dict[str, Any],
        simulation_mode: bool = False,
        request_timeout_seconds: float = 15.0,
    ):
        self.account_id = str(account_id).strip()
        if not self.account_id:
            raise ValueError("account_id is required")
        if not isinstance(connector_config, dict):
            raise ValueError("connector_config must be a dictionary")
        account_validation = connector_config.get("account_validation", {})
        if "password" in account_validation:
            raise ValueError("Literal MT5 passwords are forbidden; configure password_env")
        if not simulation_mode:
            expected_login = account_validation.get("expected_login")
            if str(expected_login or "").strip() != self.account_id:
                raise ValueError("Live worker expected_login must exactly match account_id")
            for field in ("expected_server", "terminal_path", "password_env"):
                if not str(account_validation.get(field) or "").strip():
                    raise ValueError(f"Live worker requires account_validation.{field}")
        self.connector_config = connector_config
        self.simulation_mode = bool(simulation_mode)
        self.request_timeout_seconds = float(request_timeout_seconds)
        self._process: Optional[multiprocessing.Process] = None
        self._pipe: Optional[Connection] = None
        self._lock = threading.Lock()
        self._ready: Dict[str, Any] = {}

    @property
    def connected(self) -> bool:
        return bool(self._ready.get("connected") and self._process and self._process.is_alive())

    def start(self) -> Dict[str, Any]:
        if self._process and self._process.is_alive():
            return dict(self._ready)
        context = multiprocessing.get_context("spawn")
        parent, child = context.Pipe()
        process = context.Process(
            target=_worker_main,
            args=(child, self.connector_config, self.simulation_mode),
            name=f"MQ3-MT5-{self.account_id}",
            daemon=True,
        )
        process.start()
        self._process = process
        self._pipe = parent
        if not parent.poll(self.request_timeout_seconds):
            process.terminate()
            process.join(timeout=2.0)
            self._ready = {"connected": False, "error": "MT5 worker startup timed out"}
            return dict(self._ready)
        ready = parent.recv()
        info = ready.get("account_info", {})
        if not self.simulation_mode and str(info.get("login")) != self.account_id:
            self.stop()
            self._ready = {"connected": False, "error": "Worker terminal login mismatch", "reported_login": info.get("login")}
            return dict(self._ready)
        self._ready = ready
        return dict(self._ready)

    def _call(self, command: str, **kwargs: Any) -> Any:
        if not self.connected or self._pipe is None:
            if command in {"get_account_info", "get_runtime_status"}:
                return {"available": False, "connected": False, "login": None, "data_mode": "UNAVAILABLE"}
            return {"success": False, "reason": "Account-specific MT5 worker is not connected", "mode": "LIVE_LOCKED"}
        request_id = uuid.uuid4().hex
        with self._lock:
            self._pipe.send({"request_id": request_id, "command": command, "kwargs": kwargs})
            deadline = time.monotonic() + self.request_timeout_seconds
            while time.monotonic() < deadline:
                if self._pipe.poll(min(0.25, max(0.0, deadline - time.monotonic()))):
                    response = self._pipe.recv()
                    if response.get("request_id") != request_id:
                        continue
                    if not response.get("success"):
                        return {"success": False, "reason": response.get("error", "Worker command failed"), "mode": "LIVE"}
                    return response.get("result")
        return {"success": False, "reason": f"MT5 worker command timed out: {command}", "mode": "LIVE"}

    def get_runtime_status(self) -> Dict[str, Any]:
        return self._call("get_runtime_status")

    def get_account_info(self) -> Dict[str, Any]:
        return self._call("get_account_info")

    def get_open_positions(self) -> List[Dict[str, Any]]:
        result = self._call("get_open_positions")
        return result if isinstance(result, list) else []

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        result = self._call("place_order", **kwargs)
        return result if isinstance(result, dict) else {"success": False, "reason": "Invalid worker response"}

    def modify_position(self, **kwargs: Any) -> Any:
        return self._call("modify_position", **kwargs)

    def close_position(self, **kwargs: Any) -> Any:
        return self._call("close_position", **kwargs)

    def close_partial_position(self, **kwargs: Any) -> Any:
        return self._call("close_partial_position", **kwargs)

    def emergency_close_all(self) -> int:
        result = self._call("emergency_close_all")
        return int(result) if isinstance(result, (int, float)) else 0

    def stop(self) -> None:
        if self._pipe is not None and self._process and self._process.is_alive():
            try:
                self._call("shutdown")
            except Exception:
                pass
        if self._process and self._process.is_alive():
            self._process.terminate()
        if self._process:
            self._process.join(timeout=2.0)
        self._pipe = None
        self._process = None
        self._ready = {}


class MT5TerminalFleet:
    """Lifecycle manager for independently isolated account workers."""

    def __init__(self):
        self.workers: Dict[str, MT5TerminalWorkerProxy] = {}

    def add(self, worker: MT5TerminalWorkerProxy) -> None:
        if worker.account_id in self.workers:
            raise ValueError(f"Duplicate MT5 account worker: {worker.account_id}")
        self.workers[worker.account_id] = worker

    def start_all(self) -> Dict[str, Dict[str, Any]]:
        return {account_id: worker.start() for account_id, worker in self.workers.items()}

    def stop_all(self) -> None:
        for worker in self.workers.values():
            worker.stop()

    def verified_connectors(self) -> Dict[str, MT5TerminalWorkerProxy]:
        return {account_id: worker for account_id, worker in self.workers.items() if worker.connected}
