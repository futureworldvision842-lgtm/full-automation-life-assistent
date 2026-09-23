"""Recovery checks with all process creation, termination and HTTP calls stubbed."""
import json
from unittest.mock import Mock

import pytest
from bootstrap import control, lifecycle, master_ecosystem_launcher as master, supervisor


@pytest.fixture(autouse=True)
def isolate_effects(monkeypatch, tmp_path):
    monkeypatch.setattr(master, "OVERRIDES_FILE", tmp_path / "service-overrides.json")
    monkeypatch.setattr(lifecycle, "STOP_FLAG", tmp_path / "stop")
    monkeypatch.setattr(lifecycle, "AUDIT_LOG", tmp_path / "audit.jsonl")
    monkeypatch.setattr(control, "start_supervisor", Mock(return_value={"ok": True, "supervisor": {"pid": 100, "created": 10}}))
    monkeypatch.setattr(master, "probe_http", lambda *args, **kwargs: False)
    monkeypatch.setattr(supervisor, "read_state", lambda: {})
    monkeypatch.setattr(lifecycle, "read_state", lambda: {})
    monkeypatch.setattr(supervisor.psutil, "process_iter", Mock(side_effect=AssertionError("No process scans")))
    monkeypatch.setattr(supervisor.psutil, "net_connections", Mock(side_effect=AssertionError("No port ownership scans")))


def test_catalog_uses_safe_supervisor_commands():
    specs = master._catalog()
    assert not specs["trader"]["allowed"] and not specs["discord"]["allowed"]
    assert "--demo" in specs["mq3"]["cmd"] and "--read-only" in specs["mq3"]["cmd"]
    assert specs["ollama"]["port"] == 11435
    assert "integrations" in str(specs["godseye"]["cwd"])


@pytest.mark.parametrize("key", ["trader", "trading", "discord", "dc"])
def test_high_impact_service_start_refused(key):
    result = master.start_service(key, wait=0)
    assert result["ok"] is False and result["executed"] is False
    control.start_supervisor.assert_not_called()
    assert not master.OVERRIDES_FILE.exists()


def test_port_and_pattern_apis_never_kill():
    assert master.kill_by_port(11434)["executed"] is False
    assert master.kill_by_pattern("node.exe")["executed"] is False
    assert lifecycle.free_ports([11434]) == []
    assert lifecycle.kill_process_tree(123456) is False


def test_only_recorded_owned_identities_are_selected(monkeypatch):
    state = {"supervisor": {"pid": 100, "created": 10}, "services": {
        "owned": {"pid": 200, "created": 20, "owned": True, "children": [{"pid": 201, "created": 21}]},
        "external": {"pid": 300, "created": 30, "owned": False},
    }}
    monkeypatch.setattr(lifecycle, "read_state", lambda: state)
    assert lifecycle.owned_entries(service_names={"owned"}, include_supervisor=False) == [
        {"pid": 200, "created": 20}, {"pid": 201, "created": 21}]


def test_reused_pid_is_not_terminated(monkeypatch):
    process = Mock()
    process.create_time.return_value = 99
    process.is_running.return_value = True
    monkeypatch.setattr(supervisor.psutil, "Process", lambda pid: process)
    result = lifecycle._stop_entries([{"pid": 222222, "created": 10}])
    assert result["ok"] and result["matched"] == 0
    process.terminate.assert_not_called()
    process.kill.assert_not_called()


def test_dry_run_has_no_stop_or_audit_writes():
    result = lifecycle.stop_managed_processes(dry_run=True)
    assert result["ok"] and result["dryRun"]
    assert not lifecycle.STOP_FLAG.exists() and not lifecycle.AUDIT_LOG.exists()


def test_start_receipt_does_not_claim_readiness_without_owned_process():
    result = master.start_service("dashboard", wait=0)
    assert result["ok"] is False and result["owned"] is False
    control.start_supervisor.assert_called_once()


def test_start_all_excludes_blocked_services(monkeypatch):
    seen = []
    def ready(keys, wait):
        seen.extend(keys)
        return {key: {"ok": True} for key in keys}
    monkeypatch.setattr(master, "_wait_for_services", ready)
    result = master.start_all_services(open_browser=False, wait=0)
    assert result["ok"]
    assert "trader" not in seen and "discord" not in seen
    assert {"dashboard", "mq3", "ollama", "worldmonitor", "godseye"}.issubset(seen)


def test_stop_sets_override_before_exact_identity_stop(monkeypatch):
    def stop(names):
        assert json.loads(master.OVERRIDES_FILE.read_text())["disabled"] == names
        return {"ok": True, "matched": 0, "remaining": []}
    monkeypatch.setattr(master, "stop_recorded_services", stop)
    assert master.stop_service("mq3")["ok"]


def test_overrides_preserve_other_explicit_stops():
    master._set_disabled(["MQ3 Trading Cockpit", "Odysseus AI Brain"], True)
    master._set_disabled(["MQ3 Trading Cockpit"], False)
    assert json.loads(master.OVERRIDES_FILE.read_text())["disabled"] == ["Odysseus AI Brain"]
