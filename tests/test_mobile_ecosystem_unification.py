import pytest
from fastapi.testclient import TestClient
from dashboard import app as dashboard_app
from mobile_control import app as mobile_app
import actions.android_automation as android_auto

dashboard_client = TestClient(dashboard_app)
mobile_client = TestClient(mobile_app)

def test_dashboard_mobile_view_endpoints():
    r1 = dashboard_client.get("/mobile")
    assert r1.status_code == 200
    assert "J.A.R.V.I.S. Mobile" in r1.text

    r2 = dashboard_client.get("/mobile.html")
    assert r2.status_code == 200
    assert "J.A.R.V.I.S. Mobile" in r2.text

def test_mobile_control_remote_directives():
    token = "wHUfdgY-AdHQZMb93xK5ZB-uNeYoXrQ_0p7RgTgnAhE"
    headers = {"X-Jarvis-Token": token}

    # 1. Speak
    r_speak = mobile_client.post("/api/mobile/speak", json={"text": "Assalam-o-Alaikum Master", "lang": "ur"}, headers=headers)
    assert r_speak.status_code == 200
    assert r_speak.json().get("ok") is True

    # 2. Vibrate
    r_vib = mobile_client.post("/api/mobile/vibrate", json={"pattern": [200, 100, 200]}, headers=headers)
    assert r_vib.status_code == 200
    assert r_vib.json().get("ok") is True

    # 3. Notification
    r_notif = mobile_client.post("/api/mobile/notification", json={"title": "Trade Alert", "body": "XAUUSD +1.0R Locked"}, headers=headers)
    assert r_notif.status_code == 200
    assert r_notif.json().get("ok") is True

    # 4. Launch App
    r_app = mobile_client.post("/api/mobile/launch-app", json={"app": "whatsapp"}, headers=headers)
    assert r_app.status_code == 200
    assert r_app.json().get("ok") is True

def test_jarvis_voice_mobile_commands():
    # 1. Battery query
    r_bat = dashboard_client.post("/api/jarvis/chat_voice", json={"prompt": "mobile battery kitni hai?"})
    assert r_bat.status_code == 200
    assert r_bat.json().get("action_taken") == "MOBILE_BATTERY_REPORTED"

    # 2. Siren query
    r_siren = dashboard_client.post("/api/jarvis/chat_voice", json={"prompt": "mobile par siren bajao"})
    assert r_siren.status_code == 200
    assert r_siren.json().get("action_taken") == "MOBILE_SIREN_TRIGGERED"

    # 3. WhatsApp query
    r_wa = dashboard_client.post("/api/jarvis/chat_voice", json={"prompt": "mobile par whatsapp kholo"})
    assert r_wa.status_code == 200
    assert r_wa.json().get("action_taken") == "MOBILE_WHATSAPP_LAUNCHED"

def test_android_automation_safe_fallback():
    devs = android_auto.list_connected_devices()
    assert isinstance(devs, list)
    bat = android_auto.get_mobile_battery()
    assert isinstance(bat, dict)
    res_app = android_auto.open_mobile_app("whatsapp")
    assert isinstance(res_app, str)

def test_apk_download_availability():
    r = dashboard_client.get("/api/download/apk")
    assert r.status_code == 200
    assert "application/vnd.android.package-archive" in r.headers.get("content-type", "")
