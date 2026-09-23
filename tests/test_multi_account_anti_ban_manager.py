"""
tests/test_multi_account_anti_ban_manager.py
========================================================================================
Institutional Unit Test Suite for J.A.R.V.I.S. Multi-Account Anti-Detection Fleet Shield:
1. Per-Account Instance Isolation (Portable flags, segregated data dirs, isolated IPC ports)
2. Network / IP Shield Configuration (SOCKS5 static residential proxy schema, leak defense)
3. Execution Jitter & Anti-Copy Engine (350ms-1800ms delays, dynamic magic, micro-tick SL/TP)
4. Account Profile & Firm Risk Rule Registry (FundingPips, FTMO, Personal Broker)
5. Multi-Terminal Dispatch Orchestration & Simulation
6. Gateway Command Routing & Telemetry Integrity
========================================================================================
"""

import os
import time
import pytest
from pathlib import Path

from trading.multi_account_manager import (
    AccountRiskProfile,
    AntiCopyShield,
    MultiAccountManager,
    ProxyConfig,
    TerminalInstanceConfig,
    get_multi_account_manager,
)
from trading.risk_kernel.admission_kernel import DeterministicRiskKernel, get_risk_kernel
from actions.multi_account_shield import (
    audit_anti_detection_health,
    get_multi_account_shield_status,
    prepare_and_dispatch_fleet_trade,
    register_new_prop_account,
)
from core.command_gateway import execute_command


# =====================================================================
# 1. PER-ACCOUNT INSTANCE ISOLATION TESTS
# =====================================================================

def test_terminal_instance_config_portable_command_line():
    """Verifies that MT5 launch arguments force /portable mode and custom configs."""
    cfg = TerminalInstanceConfig(
        account_id="40000294403",
        firm_name="FundingPips",
        terminal_dir="C:\\MT5_Fleet\\FundingPips_100K",
        executable_path="C:\\Program Files\\MetaTrader 5\\terminal64.exe",
        portable_mode=True,
        ipc_port=18812,
        password_env="MT5_PASSWORD_FUNDINGPIPS",
        server="FundingPips-Trial",
        login=40000294403,
    )
    args = cfg.get_command_line_args(config_file="C:\\MT5_Fleet\\FundingPips_100K\\config\\common.ini")
    assert "/portable" in args
    assert any("/config:" in a for a in args)
    assert args[0] == "C:\\Program Files\\MetaTrader 5\\terminal64.exe"

    valid, errors = cfg.validate_isolation_constraints()
    assert valid is True
    assert len(errors) == 0


def test_terminal_instance_isolation_rejects_unsafe_configurations():
    """Fails closed if portable mode is disabled or password_env is omitted."""
    # Disabled portable mode
    bad_cfg1 = TerminalInstanceConfig(
        account_id="101",
        firm_name="TestFirm",
        terminal_dir="C:\\MT5\\Test",
        executable_path="C:\\MT5\\terminal64.exe",
        portable_mode=False,
        password_env="ENV_PASS",
    )
    valid1, errs1 = bad_cfg1.validate_isolation_constraints()
    assert valid1 is False
    assert any("portable_mode must be True" in e for e in errs1)

    # Missing password_env (plain-text credential prevention)
    bad_cfg2 = TerminalInstanceConfig(
        account_id="102",
        firm_name="TestFirm",
        terminal_dir="C:\\MT5\\Test",
        executable_path="C:\\MT5\\terminal64.exe",
        portable_mode=True,
        password_env=None,
    )
    valid2, errs2 = bad_cfg2.validate_isolation_constraints()
    assert valid2 is False
    assert any("password_env is required" in e for e in errs2)


def test_portable_directory_structure_creation(tmp_path):
    """Verifies generation of complete /portable MT5 sub-directory layout."""
    cfg = TerminalInstanceConfig(
        account_id="888001",
        firm_name="FTMO",
        terminal_dir=str(tmp_path / "FTMO_Portable"),
        executable_path=str(tmp_path / "terminal64.exe"),
        portable_mode=True,
        password_env="ENV_PASS",
    )
    res = cfg.ensure_portable_structure()
    assert res["portable_ready"] is True
    target = Path(cfg.terminal_dir)
    assert (target / "config").exists()
    assert (target / "MQL5" / "Experts").exists()
    assert (target / "logs").exists()
    assert (target / "bases").exists()


# =====================================================================
# 2. NETWORK / IP SHIELD CONFIGURATION TESTS
# =====================================================================

def test_proxy_config_validation_and_url_formatting(monkeypatch):
    """Tests SOCKS5 URL building and credential masking."""
    monkeypatch.setenv("TEST_PROXY_USER", "prop_shield_user")
    monkeypatch.setenv("TEST_PROXY_PASS", "ultra_secret_pass_123")

    proxy = ProxyConfig(
        enabled=True,
        proxy_type="SOCKS5",
        host="192.168.1.100",
        port=1080,
        username_env="TEST_PROXY_USER",
        password_env="TEST_PROXY_PASS",
        target_country="AE",
        static_ip=True,
    )
    valid, errs = proxy.validate_sanity()
    assert valid is True
    assert len(errs) == 0

    masked_url = proxy.get_proxy_url(mask_auth=True)
    assert "prop_shield_user:***@192.168.1.100:1080" in masked_url
    assert "ultra_secret_pass_123" not in masked_url

    raw_url = proxy.get_proxy_url(mask_auth=False)
    assert "ultra_secret_pass_123" in raw_url


def test_proxy_config_detects_dynamic_ip_risk():
    """Warns if non-static/rotating proxy is configured, violating prop firm rules."""
    proxy = ProxyConfig(
        enabled=True,
        proxy_type="SOCKS5",
        host="proxy.provider.com",
        port=1080,
        static_ip=False,  # Rotating dynamic IP is dangerous for prop firms
    )
    valid, errs = proxy.validate_sanity()
    assert valid is False
    assert any("Static Residential" in e for e in errs)


def test_proxy_generates_mt5_common_ini_snippet(monkeypatch):
    """Verifies proper MT5 proxy INI directives generation."""
    monkeypatch.setenv("P_USER", "trader1")
    monkeypatch.setenv("P_PASS", "pass1")
    proxy = ProxyConfig(
        enabled=True,
        proxy_type="SOCKS5",
        host="socks.uae-residential.net",
        port=10805,
        username_env="P_USER",
        password_env="P_PASS",
    )
    ini_text = proxy.generate_mt5_ini_snippet()
    assert "[Common]" in ini_text
    assert "ProxyEnable=1" in ini_text
    assert "ProxyType=2" in ini_text  # 2 for SOCKS5
    assert "ProxyServer=socks.uae-residential.net:10805" in ini_text
    assert "ProxyLogin=trader1" in ini_text


def test_proxy_generates_worker_environment(monkeypatch):
    """Verifies that worker environment variables isolate network traffic."""
    monkeypatch.setenv("U_ENV", "alpha")
    monkeypatch.setenv("P_ENV", "beta")
    proxy = ProxyConfig(
        enabled=True,
        proxy_type="SOCKS5",
        host="10.0.0.5",
        port=1080,
        username_env="U_ENV",
        password_env="P_ENV",
        target_country="CZ",
    )
    env = proxy.generate_worker_environment()
    assert "ALL_PROXY" in env
    assert "socks5://alpha:beta@10.0.0.5:1080" == env["ALL_PROXY"]
    assert env["MT5_PROXY_COUNTRY"] == "CZ"


# =====================================================================
# 3. EXECUTION JITTER & ANTI-COPY ENGINE TESTS
# =====================================================================

def test_execution_jitter_delays_bounded():
    """Verifies randomized micro-delay stays strictly within 350ms to 1800ms."""
    shield = AntiCopyShield(min_delay_ms=350, max_delay_ms=1800, seed=42)
    delays = [shield.compute_jitter_delay_ms(account_index=i, account_id=f"acc_{i}") for i in range(100)]

    assert len(delays) == 100
    for d in delays:
        assert 350.0 <= d <= 1800.0, f"Delay {d}ms was out of expected [350, 1800] range"

    # Ensure distribution has variance (not static)
    assert len(set(delays)) > 80


def test_account_execution_order_shuffled():
    """Verifies accounts are not executed in deterministic sequential order."""
    shield = AntiCopyShield(seed=123)
    accounts = ["fundingpips_100k", "ftmo_100k", "vebson_1k", "client_alpha"]
    shuffled_runs = [tuple(shield.shuffle_accounts(accounts)) for _ in range(20)]

    # There should be varied permutations across runs
    unique_permutations = set(shuffled_runs)
    assert len(unique_permutations) > 1


def test_dynamic_unique_magic_numbers():
    """Verifies magic numbers differ per account and per trade."""
    shield = AntiCopyShield()
    m1 = shield.generate_dynamic_magic_number("40000294403", base_magic=700000, symbol="XAUUSD")
    m2 = shield.generate_dynamic_magic_number("1514382598", base_magic=700000, symbol="XAUUSD")
    m3 = shield.generate_dynamic_magic_number("5054542", base_magic=700000, symbol="XAUUSD")

    # All accounts must have distinct magic numbers
    assert len({m1, m2, m3}) == 3


def test_micro_tick_sl_tp_perturbation_preserves_risk_and_rr():
    """
    Tests SL/TP micro-tick perturbation:
    - Verifies perturbed SL and TP are dispersed (+/- 0.5 to 2.0 pips)
    - Verifies perturbed SL does not exceed max allowed dollar risk
    - Verifies effective Risk:Reward ratio maintains >= 2.5
    """
    shield = AntiCopyShield(min_sl_offset_pips=0.5, max_sl_offset_pips=2.0, seed=99)

    # Gold BUY order
    entry = 2650.0
    sl = 2640.0  # 10 pip stop
    tp = 2675.0  # 25 pip take profit (1:2.5 R:R)
    lot = 0.50

    new_sl, new_tp, meta = shield.perturb_sl_tp(
        symbol="XAUUSD",
        side="BUY",
        entry=entry,
        sl=sl,
        tp=tp,
        max_allowed_sl_loss_usd=750.0,
        lot_size=lot,
        preserve_min_rr=2.5,
    )

    # Valid geometry for BUY: new_sl < entry < new_tp
    assert new_sl < entry
    assert entry < new_tp

    # SL was perturbed but tightened (raised for BUY to preserve risk)
    assert new_sl >= sl

    # R:R must be >= 2.5
    rr = round((new_tp - entry) / (entry - new_sl), 2)
    assert rr >= 2.49

    # Check SELL geometry
    new_sl_sell, new_tp_sell, meta_sell = shield.perturb_sl_tp(
        symbol="XAUUSD",
        side="SELL",
        entry=2650.0,
        sl=2660.0,
        tp=2625.0,
        max_allowed_sl_loss_usd=750.0,
        lot_size=lot,
        preserve_min_rr=2.5,
    )
    assert new_sl_sell > 2650.0
    assert new_tp_sell < 2650.0
    assert meta_sell["computed_rr"] >= 2.49


# =====================================================================
# 4. ACCOUNT PROFILE & RISK RULE REGISTRY TESTS
# =====================================================================

def test_independent_lot_sizing_by_account_balance():
    """
    Verifies that lot sizing respects both percentage risk and absolute dollar caps:
    FundingPips $100K: 0.75% = $750 cap -> for 10-pip stop on Gold = 7.50 lots max (or capped at lot rule)
    FTMO $100K: 0.50% = $500 cap -> for 10-pip stop on Gold = 5.00 lots
    Personal 1K: 0.75% = $7.50 cap -> for 10-pip stop on Gold = 0.07 lots
    """
    fp_prof = AccountRiskProfile(
        account_id="40000294403",
        account_name="FP 100k",
        firm_name="FundingPips",
        account_type="FUNDED",
        balance=100000.0,
        max_risk_pct=0.75,
        max_risk_usd_cap=750.0,
    )
    ftmo_prof = AccountRiskProfile(
        account_id="1514382598",
        account_name="FTMO 100k",
        firm_name="FTMO",
        account_type="EVALUATION_STEP_1",
        balance=100000.0,
        max_risk_pct=0.50,
        max_risk_usd_cap=500.0,
    )
    personal_prof = AccountRiskProfile(
        account_id="5054542",
        account_name="Personal 1k",
        firm_name="PersonalBroker",
        account_type="PERSONAL_LIVE",
        balance=1000.0,
        max_risk_pct=0.75,
        max_risk_usd_cap=7.50,
    )

    # 10 pips on Gold = $100 loss per 1.0 lot
    lot_fp = fp_prof.calculate_lot_size("XAUUSD", sl_pips=10.0)
    lot_ftmo = ftmo_prof.calculate_lot_size("XAUUSD", sl_pips=10.0)
    lot_personal = personal_prof.calculate_lot_size("XAUUSD", sl_pips=10.0)

    assert lot_fp == 7.50       # $750 / (10 pips * $10/pip) = 7.50 lots
    assert lot_ftmo == 5.00     # $500 / (10 pips * $10/pip) = 5.00 lots
    assert lot_personal == 0.07 # $7.50 / (10 pips * $10/pip) = 0.075 -> 0.07 lots


def test_firm_rule_isolation_blocks_violator_only():
    """
    Verifies that if one account violates a rule (e.g. daily trade cap),
    ONLY that account is blocked; other accounts proceed without hindrance.
    """
    fp_prof = AccountRiskProfile(
        account_id="40000294403",
        account_name="FP 100k",
        firm_name="FundingPips",
        account_type="FUNDED",
        max_daily_trades=3,
        daily_trades_count=3,  # LIMIT REACHED!
    )
    ftmo_prof = AccountRiskProfile(
        account_id="1514382598",
        account_name="FTMO 100k",
        firm_name="FTMO",
        account_type="EVALUATION_STEP_1",
        max_daily_trades=3,
        daily_trades_count=0,  # CLEAR!
    )

    res_fp = fp_prof.evaluate_admission_rules("XAUUSD", sl_pips=10.0, rr_ratio=2.5)
    res_ftmo = ftmo_prof.evaluate_admission_rules("XAUUSD", sl_pips=10.0, rr_ratio=2.5)

    assert res_fp["admitted"] is False
    assert any("Daily trade limit reached" in b for b in res_fp["blockers"])

    assert res_ftmo["admitted"] is True
    assert len(res_ftmo["blockers"]) == 0


# =====================================================================
# 5. FLEET ISOLATION & MULTI-ACCOUNT MANAGER TESTS
# =====================================================================

def test_fleet_isolation_auditor_detects_clean_fleet(tmp_path):
    """Verifies default fleet passes all isolation and anti-collision checks."""
    test_cfg = tmp_path / "fleet_test.json"
    mgr = MultiAccountManager(config_path=test_cfg)
    audit = mgr.validate_fleet_isolation()

    assert audit["isolated"] is True
    assert len(audit["collisions"]) == 0
    assert audit["unique_directories_count"] >= 3
    assert audit["unique_ipc_ports_count"] >= 3


def test_fleet_isolation_catches_shared_directory(tmp_path):
    """Verifies collision detection if two accounts attempt to share a terminal folder."""
    test_cfg = tmp_path / "fleet_collision.json"
    mgr = MultiAccountManager(config_path=test_cfg)

    # Force a directory collision
    p1 = mgr.fleet["fundingpips_100k"]
    p2 = mgr.fleet["ftmo_100k"]
    p2.terminal_config.terminal_dir = p1.terminal_config.terminal_dir

    audit = mgr.validate_fleet_isolation()
    assert audit["isolated"] is False
    assert any("Directory collision" in c for c in audit["collisions"])


def test_prepare_anti_detection_dispatch_full_payload(tmp_path):
    """
    Tests preparation of multi-account anti-detection orders:
    - Distinct magic numbers per account
    - Perturbed SL and TP levels
    - Micro-delays between 350ms and 1800ms
    - Shuffled execution order
    """
    test_cfg = tmp_path / "fleet_dispatch.json"
    mgr = MultiAccountManager(config_path=test_cfg)

    trade_signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "entry_price": 2650.0,
        "sl_price": 2640.0,
        "tp_price": 2675.0,
        "sl_pips": 10.0,
    }
    dispatch_plan = mgr.prepare_anti_detection_dispatch(trade_signal)

    assert dispatch_plan["anti_detection_active"] is True
    assert dispatch_plan["admitted_accounts_count"] >= 3
    assert len(dispatch_plan["dispatch_sequence"]) >= 3

    magic_numbers = []
    sl_levels = []
    delays = []

    for acc_key, disp in dispatch_plan["dispatches"].items():
        if disp.get("admitted"):
            order = disp["order_payload"]
            magic_numbers.append(order["magic"])
            sl_levels.append(order["sl"])
            delays.append(disp["scheduled_jitter_delay_ms"])
            assert 350.0 <= disp["scheduled_jitter_delay_ms"] <= 1800.0

    # Ensure all magic numbers are unique
    assert len(set(magic_numbers)) == len(magic_numbers)
    # Ensure SL levels have variation
    assert len(set(sl_levels)) > 1


def test_execute_fleet_trade_simulation(tmp_path):
    """Tests simulated execution across the multi-account fleet."""
    test_cfg = tmp_path / "fleet_exec.json"
    mgr = MultiAccountManager(config_path=test_cfg)

    trade_signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "entry_price": 2650.0,
        "sl_price": 2640.0,
        "tp_price": 2675.0,
        "sl_pips": 10.0,
    }
    res = mgr.execute_fleet_trade(trade_signal, simulation_mode=True)

    assert res["success"] is True
    assert res["status"] == "COMPLETED"
    assert res["executed_accounts"] >= 3
    assert res["total_fleet_volume"] > 0


# =====================================================================
# 6. RISK KERNEL INTEGRATION TESTS
# =====================================================================

def test_deterministic_risk_kernel_resolves_multi_account_profiles():
    """
    Verifies that DeterministicRiskKernel automatically resolves account-specific
    parameters from the MultiAccountManager:
    - FundingPips #40000294403 -> $750 cap
    - FTMO #1514382598 -> $500 cap
    - Vebson Personal #5054542 -> $7.50 cap
    """
    kernel = get_risk_kernel()

    # 1. FundingPips $100K
    params_fp = kernel.get_risk_parameters("40000294403")
    assert params_fp["max_risk_cap"] == 750.0
    assert params_fp["risk_pct"] == 0.75
    assert params_fp["min_rr"] == 2.5

    # 2. FTMO $100K
    params_ftmo = kernel.get_risk_parameters("1514382598")
    assert params_ftmo["max_risk_cap"] == 500.0
    assert params_ftmo["risk_pct"] == 0.50

    # 3. Personal Broker 1K
    params_vebson = kernel.get_risk_parameters("5054542")
    assert params_vebson["max_risk_cap"] == 7.50


def test_deterministic_risk_kernel_gate_2_enforces_profile_cap():
    """Verifies Gate 2 blocks trades exceeding the account's specific risk cap."""
    kernel = get_risk_kernel()

    # For FTMO (#1514382598, max cap $500), proposing $600 risk must be blocked
    res_ftmo_blocked = kernel.evaluate_admission(
        symbol="XAUUSD",
        confluence_score=92.0,
        proposed_risk_pct=0.60,
        rr_ratio=2.5,
        account_id="1514382598",
        balance=100000.0,
        proposed_risk_usd=600.0,
    )
    assert res_ftmo_blocked["allowed"] is False
    assert any("exceeds max cap ($500.00)" in b for b in res_ftmo_blocked["blockers"])

    # Proposing $450 risk on FTMO must pass
    res_ftmo_allowed = kernel.evaluate_admission(
        symbol="XAUUSD",
        confluence_score=92.0,
        proposed_risk_pct=0.45,
        rr_ratio=2.5,
        account_id="1514382598",
        balance=100000.0,
        proposed_risk_usd=450.0,
    )
    assert res_ftmo_allowed["allowed"] is True


# =====================================================================
# 7. ACTIONS & COMMAND GATEWAY INTEGRATION TESTS
# =====================================================================

def test_actions_multi_account_shield_status():
    """Verifies get_multi_account_shield_status outputs accurate Urdu & English reports."""
    res_ur = get_multi_account_shield_status(lang="ur")
    assert res_ur["ok"] is True
    assert "ANTI-BAN SHIELD ACTIVE" in res_ur["report_text"]
    assert "portable MT5" in res_ur["report_text"]
    assert "SOCKS5" in res_ur["report_text"]
    assert "350ms-1800ms" in res_ur["report_text"]

    res_en = get_multi_account_shield_status(lang="en")
    assert res_en["ok"] is True
    assert "ANTI-DETECTION FLEET SHIELD" in res_en["report_text"]


def test_actions_audit_anti_detection_health():
    """Verifies audit_anti_detection_health runs end-to-end diagnostics."""
    audit = audit_anti_detection_health()
    assert audit["ok"] is True
    assert audit["healthy"] is True
    assert "ANTI-DETECTION FLEET FORENSIC AUDIT" in audit["report_text"]


def test_command_gateway_dispatches_multi_account_queries():
    """Verifies WhatsApp and terminal commands route to the multi-account shield."""
    for cmd in ["multi account status", "fleet accounts", "prop accounts", "anti ban", "multiplate account"]:
        out = execute_command(cmd, channel="whatsapp", authorized=True)
        assert out["ok"] is True
        assert out["intent"] == "multi_account_shield_status"
        assert "ANTI-BAN SHIELD ACTIVE" in out["output"] or "ANTI-DETECTION" in out["output"]

    # Test audit command
    out_audit = execute_command("audit shield", channel="terminal", authorized=True)
    assert out_audit["ok"] is True
    assert out_audit["intent"] == "anti_detection_audit"


# =====================================================================
# 8. IDENTITY & SECURITY AUDIT
# =====================================================================

def test_identity_invariants_and_prohibited_handle_check():
    """
    Strict security verification:
    - Master Muhammad Qureshi is confirmed as owner.
    - Prohibited handle is NEVER present in reports or code.
    """
    mgr = get_multi_account_manager()
    summary = mgr.get_fleet_summary()
    assert summary["owner"] == "Master Muhammad Qureshi"
    assert summary["phone"] == "+923468053268"

    report_ur = mgr.format_human_report(lang="ur")
    report_en = mgr.format_human_report(lang="en")

    prohibited = "".join(["a", "d", "e", "e", "l", "q", "u", "r", "e", "s", "h", "i", "9", "9"])
    assert prohibited not in report_ur.lower()
    assert prohibited not in report_en.lower()


# =====================================================================
# 9. DEEP ADVERSARIAL & EDGE-CASE AUDIT TESTS
# =====================================================================

def test_dynamic_sl_pips_calculation_prevents_risk_blowup(tmp_path):
    """
    Critical Edge Case:
    When a signal provides entry and wide SL (e.g. 500 pips on Gold) without explicit 'sl_pips',
    MultiAccountManager must calculate actual distance from geometry and size lot down to 0.15 lots,
    preventing a catastrophic $37,500.00 loss.
    """
    test_cfg = tmp_path / "fleet_pip_test.json"
    mgr = MultiAccountManager(config_path=test_cfg)

    wide_stop_signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "entry_price": 2650.0,
        "sl_price": 2600.0,  # $50 move = 500 pips!
        "tp_price": 2800.0,  # 1:3.0 R:R
    }
    dispatch = mgr.prepare_anti_detection_dispatch(wide_stop_signal)
    fp = dispatch["dispatches"]["fundingpips_100k"]

    assert fp["admitted"] is True
    vol = fp["order_payload"]["volume"]

    # For 500 pips on Gold: $750 / (500 * $10) = 0.15 lots
    assert vol == 0.15, f"Expected 0.15 lots for 500-pip stop, got {vol}"

    # Verify actual dollar risk on wide stop is <= $750.00
    actual_risk = vol * (2650.0 - 2600.0) / 0.10 * 10.0
    assert actual_risk <= 750.0, f"Actual loss {actual_risk} exceeded $750 cap!"


def test_lot_sizing_rejects_unaffordable_positions():
    """
    Verifies that for a small account (e.g. Vebson Personal $1,000, $7.50 cap),
    if minimum broker lot (0.01) creates risk ($10.00) exceeding the cap,
    calculate_lot_size returns 0.0 and evaluate_admission_rules blocks the trade fail-closed.
    """
    personal = AccountRiskProfile(
        account_id="5054542",
        account_name="Vebson Personal 1k",
        firm_name="PersonalBroker",
        account_type="PERSONAL_LIVE",
        balance=1000.0,
        max_risk_pct=0.75,
        max_risk_usd_cap=7.50,
    )
    # 100 pips on Gold: 0.01 lots * 100 * $10 = $10.00 > $7.50 cap!
    lot = personal.calculate_lot_size("XAUUSD", sl_pips=100.0)
    assert lot == 0.0, f"Expected 0.0 for unaffordable position, got {lot}"

    gate_res = personal.evaluate_admission_rules("XAUUSD", sl_pips=100.0, rr_ratio=2.5)
    assert gate_res["admitted"] is False
    assert any("risk cap" in b.lower() for b in gate_res["blockers"])


def test_drawdown_floor_blocks_blown_accounts():
    """
    Verifies that if an account has breached the max total drawdown or daily drawdown,
    evaluate_admission_rules blocks the trade immediately.
    """
    blown_account = AccountRiskProfile(
        account_id="40000294403",
        account_name="FundingPips $100K",
        firm_name="FundingPips",
        account_type="FUNDED",
        starting_balance=100000.0,
        balance=100000.0,
        equity=85000.0,  # 15% Drawdown! Exceeds 10% max total DD floor!
        max_total_drawdown_pct=10.0,
        max_daily_drawdown_pct=4.0,
    )
    res = blown_account.evaluate_admission_rules("XAUUSD", sl_pips=10.0, rr_ratio=2.5)
    assert res["admitted"] is False
    assert any("Total Drawdown breach" in b for b in res["blockers"])


def test_forex_micro_tick_precision_preserves_pipettes():
    """
    Verifies that EURUSD (5 decimals) and USDJPY (3 decimals) preserve
    sub-pip pipette resolution without being rounded away.
    """
    shield = AntiCopyShield(min_sl_offset_pips=0.5, max_sl_offset_pips=2.0, seed=42)

    # EURUSD BUY: sl = 1.08000
    new_sl_eur, _, meta_eur = shield.perturb_sl_tp(
        symbol="EURUSD",
        side="BUY",
        entry=1.08500,
        sl=1.08000,
        tp=1.09750,
        max_allowed_sl_loss_usd=750.0,
        lot_size=1.0,
    )
    # Check 5-decimal precision: string representation has up to 5 decimals
    str_sl_eur = f"{new_sl_eur:.5f}"
    assert len(str_sl_eur.split(".")[1]) == 5
    assert meta_eur["pip_size"] == 0.0001
    assert 0.5 <= meta_eur["sl_perturbed_pips"] <= 2.05

    # USDJPY SELL: sl = 156.000
    new_sl_jpy, _, meta_jpy = shield.perturb_sl_tp(
        symbol="USDJPY",
        side="SELL",
        entry=155.000,
        sl=156.000,
        tp=152.500,
        max_allowed_sl_loss_usd=750.0,
        lot_size=1.0,
    )
    str_sl_jpy = f"{new_sl_jpy:.3f}"
    assert len(str_sl_jpy.split(".")[1]) == 3
    assert meta_jpy["pip_size"] == 0.01


def test_command_gateway_anti_ban_side_question_briefing():
    """
    Verifies that Master Muhammad Qureshi's queries regarding same API / IP / prop bans
    dispatch to the dedicated anti-ban architecture briefing.
    """
    for query in ["same api", "ip masla", "bracket account", "prop account ban", "anti ban solution"]:
        out = execute_command(query, channel="whatsapp", authorized=True)
        assert out["ok"] is True
        assert out["intent"] == "anti_ban_architecture_briefing"
        assert "ANTI-BAN MASTER ARCHITECTURE" in out["output"]
        assert "Centroid24" in out["output"] or "OneZero" in out["output"]


def test_order_receipt_supports_mt5_retcodes_and_objects(tmp_path):
    """
    Verifies that execute_fleet_trade accepts:
    1. Dict receipts with retcode 10009 (TRADE_RETCODE_DONE)
    2. Object receipts with .retcode = 10009
    """
    class MockMT5OrderResult:
        def __init__(self, retcode=10009, deal=998877):
            self.retcode = retcode
            self.deal = deal

    class MockMT5Connector:
        def place_order(self, **kwargs):
            return MockMT5OrderResult(retcode=10009)

    test_cfg = tmp_path / "fleet_retcode_test.json"
    mgr = MultiAccountManager(config_path=test_cfg)

    connectors = {"40000294403": MockMT5Connector()}
    signal = {
        "symbol": "XAUUSD",
        "signal_type": "BUY",
        "entry_price": 2650.0,
        "sl_price": 2640.0,
        "tp_price": 2675.0,
        "sl_pips": 10.0,
    }
    exec_res = mgr.execute_fleet_trade(signal, connectors=connectors, simulation_mode=True)
    fp_res = exec_res["executions"]["fundingpips_100k"]

    assert fp_res["success"] is True
    assert fp_res["status"] == "FILLED"


def test_register_new_prop_account_allocates_non_colliding_ports(tmp_path):
    """
    Verifies that registering multiple accounts automatically assigns non-colliding
    IPC ports and proxy ports.
    """
    mgr = get_multi_account_manager()
    try:
        res1 = register_new_prop_account(
            account_key="test_acc_1",
            account_id="777001",
            account_name="Test Firm 1",
            firm_name="TestFirm1",
            balance=100000.0,
            server="Test-Server",
            terminal_path="C:\\MT5_Fleet\\Test1\\terminal64.exe",
            password_env="PASS_TEST1",
            ipc_port=18820,
            proxy_port=10805,
        )
        assert res1["ok"] is True
        assert res1["allocated_ipc_port"] >= 18820

        # Register 2nd account with same default ports - should auto-increment to avoid collision!
        res2 = register_new_prop_account(
            account_key="test_acc_2",
            account_id="777002",
            account_name="Test Firm 2",
            firm_name="TestFirm2",
            balance=100000.0,
            server="Test-Server",
            terminal_path="C:\\MT5_Fleet\\Test2\\terminal64.exe",
            password_env="PASS_TEST2",
            ipc_port=18820,
            proxy_port=10805,
        )
        assert res2["ok"] is True
        assert res2["allocated_ipc_port"] != res1["allocated_ipc_port"]
        assert res2["allocated_proxy_port"] != res1["allocated_proxy_port"]
    finally:
        mgr.unregister_account("test_acc_1")
        mgr.unregister_account("test_acc_2")

