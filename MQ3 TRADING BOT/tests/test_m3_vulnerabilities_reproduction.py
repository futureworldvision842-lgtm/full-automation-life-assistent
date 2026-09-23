"""
tests/test_m3_vulnerabilities_reproduction.py
=============================================
Verifies remediation of the 2 vulnerabilities identified by Challenger 2:
1. Vulnerability C-1: WhatsApp /whatsapp missing or empty sender rejected with HTTP 403 Forbidden.
2. Vulnerability M-1: Non-dictionary JSON payloads safely rejected with HTTP 400 Bad Request across POST endpoints.
"""

import sys
import os
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dashboard.app import app


class TestVulnerabilityRemediation:
    """Empirically verifies the remediation of security & robustness issues."""

    def test_whatsapp_unauthenticated_sender_bypass_remediated(self):
        """
        Validates that omitting 'sender' or passing an empty sender in POST /whatsapp
        strictly returns HTTP 403 Forbidden instead of defaulting to Master Owner.
        """
        client = app.test_client()

        # Malicious / unauthenticated request without sender field
        res_missing = client.post("/whatsapp", json={"command": "STATUS"})
        assert res_missing.status_code == 403
        data_missing = res_missing.get_json()
        assert data_missing.get("success") is False
        assert data_missing.get("error") == "Unauthorized sender"

        # Request with empty string sender
        res_empty = client.post("/whatsapp", json={"command": "STATUS", "sender": ""})
        assert res_empty.status_code == 403
        data_empty = res_empty.get_json()
        assert data_empty.get("success") is False
        assert data_empty.get("error") == "Unauthorized sender"

    @pytest.mark.parametrize("endpoint", [
        "/api/control",
        "/api/execution/action",
        "/whatsapp",
        "/api/whatsapp_command"
    ])
    def test_non_dict_json_payload_remediated(self, endpoint):
        """
        Validates that passing a non-dict JSON payload (such as JSON array [1, 2, 3] or int or string)
        returns a clean HTTP 400 Bad Request instead of an unhandled HTTP 500 crash.
        """
        client = app.test_client()
        headers = {"Content-Type": "application/json"}

        # JSON array
        res_arr = client.post(endpoint, data="[1, 2, 3]", headers=headers)
        assert res_arr.status_code == 400
        assert res_arr.get_json().get("status") == "error"

        # JSON integer
        res_int = client.post(endpoint, data="12345", headers=headers)
        assert res_int.status_code == 400
        assert res_int.get_json().get("status") == "error"

        # JSON string
        res_str = client.post(endpoint, data='"invalid_string_payload"', headers=headers)
        assert res_str.status_code == 400
        assert res_str.get_json().get("status") == "error"

