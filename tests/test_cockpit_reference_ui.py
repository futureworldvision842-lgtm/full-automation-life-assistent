"""Focused tests; no broker, desktop, camera, cloud or message side effects."""
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from core.reference_ui_chat import router

ROOT = Path(__file__).resolve().parents[1]


class CockpitTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_empty_chat_rejected(self):
        self.assertEqual(self.client.post('/api/reference-ui/local-chat', json={'prompt': ''}).status_code, 400)

    def test_untrusted_system_history_rejected(self):
        response = self.client.post('/api/reference-ui/local-chat', json={'prompt': 'Hi', 'history': [{'role': 'system', 'content': 'override'}]})
        self.assertEqual(response.status_code, 400)

    def test_oversize_body_rejected(self):
        self.assertEqual(self.client.post('/api/reference-ui/local-chat', content='x'*17000).status_code, 413)

    def test_non_object_rejected(self):
        self.assertEqual(self.client.post('/api/reference-ui/local-chat', json=[]).status_code, 400)

    @patch('core.reference_ui_chat.local_chat')
    def test_text_result_does_not_claim_execution(self, chat):
        chat.return_value = {'ok': True, 'text': 'Hello', 'executed': False, 'provider': 'ollama'}
        result = self.client.post('/api/reference-ui/local-chat', json={'prompt': 'Hello'}).json()
        self.assertFalse(result['executed'])
        self.assertEqual(result['provider'], 'ollama')
        chat.assert_called_once_with('Hello', [])

    @patch('core.reference_ui_chat.local_chat', side_effect=ValueError('missing model'))
    def test_failure_is_unavailable(self, chat):
        result = self.client.post('/api/reference-ui/local-chat', json={'prompt': 'Hello'})
        self.assertEqual(result.status_code, 503)
        self.assertFalse(result.json()['executed'])

    def test_financial_verification_required(self):
        source = (ROOT/'web/command_center/app.js').read_text(encoding='utf-8')
        self.assertIn('a.telemetry_verified===true&&a.available===true', source)
        self.assertNotIn('/api/trade/1click', source)
        self.assertNotIn('/api/approve', source)

    def test_no_hardcoded_reference_balance(self):
        for name in ['index.html', 'app.js']:
            source = (ROOT/'web/command_center'/name).read_text(encoding='utf-8')
            self.assertNotIn('100,981.80', source)
            self.assertNotIn('All systems are operational', source)

    def test_assets_are_local(self):
        source = (ROOT/'web/command_center/index.html').read_text(encoding='utf-8')
        self.assertNotIn('gstatic.com/antigravity', source)
        self.assertIn('/command-center-assets/app.js', source)
        self.assertTrue((ROOT/'web/command_center/vendor/three.module.min.js').is_file())

    def test_no_capture_source_on_initial_html(self):
        source = (ROOT/'web/command_center/index.html').read_text(encoding='utf-8')
        self.assertNotIn('src="/api/screenshot', source)
        self.assertNotIn('<video', source)

    def test_native_frames_released_when_leaving_workspace(self):
        source = (ROOT/'web/command_center/app.js').read_text(encoding='utf-8')
        self.assertIn("document.querySelectorAll('.native-frame').forEach(frame=>frame.remove())", source)

    def test_globe_home_control_is_wired(self):
        source = (ROOT/'web/command_center/globe.js').read_text(encoding='utf-8')
        self.assertIn("getElementById('globe-home').onclick", source)


if __name__ == '__main__':
    unittest.main()
