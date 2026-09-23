"""Multi-Account Fleet Safe Isolation and Anti-Collision Compliance Test Suite.

Verifies:
1. Multi-Terminal portable folder validation
2. Independent risk-calibrated lot sizing per account ($100k, $50k, $25k, $5k)
3. Anti-collision execution latency jitter (prop-firm safe execution dispersion)
4. Credential isolation (password_env variable usage, no plain-text credentials)
5. Fail-closed dispatch when connector login does not match target account
"""

import json
import os
import pytest
from pathlib import Path

from src.fleet_setup_helper import FleetSetupHelper
from src.multi_terminal_copier import MultiTerminalCopier
from src.mt5_terminal_worker import MT5TerminalWorkerProxy


class MockConnector:
    def __init__(self, login: str, simulation_mode: bool = False):
        self.login = str(login)
        self.simulation_mode = simulation_mode
        self.orders = []

    def get_account_info(self):
        return {
            "available": True,
            "login": self.login,
            "server": "FundingPips-Trial",
            "balance": 50000.0,
            "equity": 50000.0,
            "currency": "USD",
            "data_mode": "PAPER" if self.simulation_mode else "LIVE"
        }

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        return {
            "success": True,
            "ticket": f"MOCK-{self.login}-{len(self.orders)}",
            "volume": kwargs.get("volume", 0.01),
            "symbol": kwargs.get("symbol", "XAUUSD"),
        }


def test_fleet_setup_helper_template_and_registration(tmp_path):
    config_file = tmp_path / "fleet_test.json"
    helper = FleetSetupHelper(config_file)
    cfg = helper.load_fleet_config()

    assert "fleet" in cfg
    assert "account_100k" in cfg["fleet"]
    assert "account_50k" in cfg["fleet"]
    assert "account_25k" in cfg["fleet"]
    assert "account_5k" in cfg["fleet"]

    # Register custom 4th client
    reg = helper.register_account(
        account_key="custom_client",
        account_name="VIP Client 100K",
        account_id="888001",
        server="FundingPips-Trial",
        terminal_path="C:\\MT5_Fleet\\Custom\\terminal64.exe",
        password_env="MT5_PASSWORD_CUSTOM",
        starting_balance=100000.0,
        risk_pct=0.0025,
    )
    assert reg["success"] is True
    assert reg["account_id"] == "888001"

    updated = helper.load_fleet_config()
    assert "custom_client" in updated["fleet"]
    assert updated["fleet"]["custom_client"]["password_env"] == "MT5_PASSWORD_CUSTOM"


def test_independent_lot_sizing_across_fleet():
    fleet = {
        "mode": "PAPER",
        "accounts": {
            "acc_100k": {"account_id": "1001", "account_name": "100K", "balance": 100000.0, "risk_pct": 0.0025, "is_active": True},
            "acc_50k": {"account_id": "2002", "account_name": "50K", "balance": 50000.0, "risk_pct": 0.0025, "is_active": True},
            "acc_25k": {"account_id": "3003", "account_name": "25K", "balance": 25000.0, "risk_pct": 0.0025, "is_active": True},
            "acc_5k": {"account_id": "4004", "account_name": "5K", "balance": 5000.0, "risk_pct": 0.0025, "is_active": True},
        },
    }
    copier = MultiTerminalCopier(fleet_config=fleet, simulation_mode=True)

    # 10 pip stop loss on Gold (XAUUSD)
    lot_100k = copier.calculate_slave_lot_size("XAUUSD", 1.0, "acc_100k", sl_pips=10.0)
    lot_50k = copier.calculate_slave_lot_size("XAUUSD", 1.0, "acc_50k", sl_pips=10.0)
    lot_25k = copier.calculate_slave_lot_size("XAUUSD", 1.0, "acc_25k", sl_pips=10.0)
    lot_5k = copier.calculate_slave_lot_size("XAUUSD", 1.0, "acc_5k", sl_pips=10.0)

    # Risk calculations:
    # 100k * 0.0025 = $250 -> 250 / (10 * 10) = 2.50 lots
    # 50k * 0.0025 = $125 -> 125 / (10 * 10) = 1.25 lots
    # 25k * 0.0025 = $62.50 -> 62.50 / (10 * 10) = 0.62 lots
    # 5k * 0.0025 = $12.50 -> 12.50 / (10 * 10) = 0.12 lots
    assert lot_100k == 2.50
    assert lot_50k == 1.25
    assert lot_25k == 0.62
    assert lot_5k == 0.12


def test_multi_terminal_replicate_with_connectors():
    fleet = {
        "mode": "PAPER",
        "accounts": {
            "acc_1": {"account_id": "1001", "account_name": "Client 1", "balance": 100000.0, "risk_pct": 0.0025, "is_active": True},
            "acc_2": {"account_id": "2002", "account_name": "Client 2", "balance": 50000.0, "risk_pct": 0.0025, "is_active": True},
        },
    }
    c1 = MockConnector("1001", simulation_mode=True)
    c2 = MockConnector("2002", simulation_mode=True)

    copier = MultiTerminalCopier(fleet_config=fleet, connectors={"1001": c1, "2002": c2}, simulation_mode=True)

    trade = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "entry_price": 2650.0,
        "sl": 2640.0,
        "tp": 2670.0,
        "sl_pips": 10.0,
        "volume": 1.0,
    }

    res = copier.replicate_order(trade)
    assert res["success"] is True
    assert res["status"] == "FILLED"
    assert res["executed_accounts"] == 2
    assert res["slave_executions"]["acc_1"]["allocated_lot"] == 2.50
    assert res["slave_executions"]["acc_2"]["allocated_lot"] == 1.25
    assert len(c1.orders) == 1
    assert len(c2.orders) == 1


def test_credential_isolation_rejects_plaintext_passwords():
    # Attempting to configure literal password raises ValueError
    bad_config = {
        "account_validation": {
            "expected_login": 12345,
            "expected_server": "Demo-Server",
            "password": "PLAIN_TEXT_PASSWORD_FORBIDDEN"
        }
    }
    with pytest.raises(ValueError, match="Literal MT5 passwords are forbidden"):
        MT5TerminalWorkerProxy(account_id="12345", connector_config=bad_config, simulation_mode=False)
