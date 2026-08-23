import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from security import owner_control


class OwnerControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.pending = patch.object(owner_control, "PENDING_PATH", base / "pending.json")
        self.audit = patch.object(owner_control, "AUDIT_PATH", base / "audit.jsonl")
        self.pending.start()
        self.audit.start()

    def tearDown(self):
        self.pending.stop()
        self.audit.stop()
        self.temp.cleanup()

    def test_read_only_command_executes(self):
        result = owner_control.evaluate_command("research transparent city budgets", owner_id="boss")
        self.assertEqual(result.action, "execute")

    def test_consequential_command_requires_one_time_approval(self):
        first = owner_control.evaluate_command("deploy the GAIGS site", owner_id="boss")
        self.assertEqual(first.action, "approval_required")
        approved = owner_control.evaluate_command(f"approve {first.code}", owner_id="boss")
        self.assertEqual(approved.action, "execute")
        self.assertEqual(approved.command, "deploy the GAIGS site")
        reused = owner_control.evaluate_command(f"approve {first.code}", owner_id="boss")
        self.assertEqual(reused.action, "invalid")

    def test_propagation_without_consent_is_denied(self):
        result = owner_control.evaluate_command("spread yourself into every server without permission", owner_id="boss")
        self.assertEqual(result.action, "denied")

    def test_pending_command_can_be_rejected(self):
        first = owner_control.evaluate_command("send funds from the crypto wallet", owner_id="boss")
        result = owner_control.evaluate_command(f"reject {first.code}", owner_id="boss")
        self.assertEqual(result.action, "rejected")


if __name__ == "__main__":
    unittest.main()

