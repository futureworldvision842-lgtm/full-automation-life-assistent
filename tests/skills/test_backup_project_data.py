"""Automated Companion Unit Test for dynamic skill: backup_project_data"""

import unittest
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestDynamicSkill_backup_project_data(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = importlib.import_module("skills.backup_project_data")

    def test_manifest_structure(self):
        self.assertTrue(hasattr(self.mod, "MANIFEST"), "Module must expose MANIFEST")
        manifest = self.mod.MANIFEST
        self.assertIsInstance(manifest, dict)
        self.assertEqual(manifest.get("name"), "backup_project_data")
        self.assertIn("description", manifest)
        self.assertIn("parameters", manifest)

    def test_run_is_callable(self):
        self.assertTrue(hasattr(self.mod, "run"), "Module must expose run()")
        self.assertTrue(callable(self.mod.run), "run attribute must be callable")

    def test_run_with_valid_parameters(self):
        params = {"source_dir": "test_sample", "target_dir": "test_sample", "tag": "test_sample"}
        output = self.mod.run(params)
        self.assertIsNotNone(output)
        self.assertIsInstance(output, (str, dict))
        if isinstance(output, str):
            self.assertGreater(len(output), 0)

    def test_run_with_none_parameters(self):
        output = self.mod.run(None)
        self.assertIsNotNone(output)
        self.assertIsInstance(output, (str, dict))

    def test_run_with_empty_parameters(self):
        output = self.mod.run({})
        self.assertIsNotNone(output)
        self.assertIsInstance(output, (str, dict))

    def test_run_with_speak_callback(self):
        spoken_messages = []
        def mock_speak(text: str):
            spoken_messages.append(text)

        output = self.mod.run({}, speak=mock_speak)
        self.assertIsNotNone(output)


if __name__ == "__main__":
    unittest.main()
