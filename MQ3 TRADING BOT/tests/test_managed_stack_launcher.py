"""Safety and wiring tests for the one-click MQ3/Jarvis managed stack."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.jarvis_full_power_master import JarvisFullPowerMaster
from src.whatsapp_notifier import WhatsAppNotifier


ROOT = Path(__file__).resolve().parents[1]


def test_stack_controller_allows_only_paper_or_locked_broker_demo_and_manages_exact_processes():
    script = (ROOT / "scripts" / "mq3_stack.ps1").read_text(encoding="utf-8")

    assert 'real-money execution.live_enabled must remain false' in script
    assert 'execution.default_mode must be \'paper\' or \'broker_demo\'' in script
    assert 'demo_order_execution_enabled' in script
    assert '"--demo"' in script and '"--sim"' in script
    assert 'MQ3_FORCE_BROKER_DEMO' in script
    assert 'Remove-Item Env:MQ3_LIVE_TRADING_CONFIRMATION' in script
    assert 'Remove-Item Env:MQ3_DEMO_TRADING_CONFIRMATION' in script
    assert 'Get-ValidatedManagedProcess' in script
    assert 'Stop-Process -Id ([int]$managed.ProcessId)' in script
    assert 'run.py", "--live"' not in script


def test_desktop_launchers_call_the_managed_controller():
    start = (ROOT / "MQ3_START.cmd").read_text(encoding="utf-8")
    stop = (ROOT / "MQ3_STOP.cmd").read_text(encoding="utf-8")

    assert "mq3_stack.ps1" in start and "-Action Start" in start
    assert "-OpenDashboard" in start
    assert "mq3_stack.ps1" in stop and "-Action Stop" in stop


def test_whatsapp_bridge_mutations_require_ephemeral_token():
    source = (ROOT / "whatsapp_bridge" / "server.js").read_text(encoding="utf-8")

    assert "function requireBridgeToken" in source
    assert "crypto.timingSafeEqual" in source
    assert "app.post('/send_group', requireBridgeToken" in source
    assert "app.post('/send', requireBridgeToken" in source
    assert "app.post('/reset_pairing', requireBridgeToken" in source


def test_notifier_attaches_bridge_token(monkeypatch):
    monkeypatch.setenv("MQ3_BRIDGE_TOKEN", "ephemeral-test-token")
    notifier = WhatsAppNotifier.__new__(WhatsAppNotifier)
    notifier.BRIDGE_URL = "http://127.0.0.1:3001"
    notifier.is_connected = False
    response = MagicMock(status_code=503)
    post = MagicMock(return_value=response)
    monkeypatch.setattr("src.whatsapp_notifier.requests.post", post)

    assert notifier.send_message("local integration test") is False
    assert post.call_args.kwargs["headers"] == {
        "X-MQ3-Bridge-Token": "ephemeral-test-token"
    }


def test_jarvis_unattended_actions_and_hid_are_config_gated():
    jarvis = JarvisFullPowerMaster.__new__(JarvisFullPowerMaster)
    jarvis.unattended_broadcasts_enabled = False
    jarvis.system_control_active = False
    jarvis.screen_vision_active = False
    jarvis.whatsapp = MagicMock()
    jarvis.vision = MagicMock()

    assert jarvis._send_unattended_alert("test", label="test") is False
    jarvis.whatsapp.send_message.assert_not_called()
    with pytest.raises(PermissionError):
        jarvis.move_mouse(10, 20)
    with pytest.raises(PermissionError):
        jarvis.click_at(10, 20)
    with pytest.raises(PermissionError):
        jarvis.press_key("ctrl+s")
    with pytest.raises(PermissionError):
        jarvis.take_screenshot("must-not-exist.png")
    jarvis.vision.move_and_click.assert_not_called()
    jarvis.vision.send_keyboard_shortcut.assert_not_called()
    jarvis.vision.capture_screen.assert_not_called()
