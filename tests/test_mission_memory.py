import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import mission_memory


class MissionMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_patch = patch.object(mission_memory, "DB_PATH", Path(self.temp.name) / "mission.db")
        self.db_patch.start()

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def test_remember_recall_and_prompt_context(self):
        memory_id = mission_memory.remember("Communities keep final decision authority.", source="owner-test")
        self.assertGreater(memory_id, 0)
        rows = mission_memory.recall("community authority")
        self.assertEqual(rows[0]["source"], "owner-test")
        prompt = mission_memory.build_prompt_context("community authority")
        self.assertIn("AI informs and assists; humans decide", prompt)
        self.assertIn("Communities keep final decision authority", prompt)
        self.assertIn("Never self-propagate", prompt)

    def test_daily_report_round_trip(self):
        mission_memory.save_daily_report("Daily test report", "2099-01-01")
        self.assertEqual(mission_memory.latest_daily_report(), "Daily test report")


if __name__ == "__main__":
    unittest.main()

