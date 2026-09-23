"""
tests/test_adversarial_m2_2_visuals.py — Empirical Challenger M2.2 Test Suite
=============================================================================
Adversarially challenge visual routes in `dashboard.py`:
1. Advanced path traversal attacks: `%2e%2e%2f`, null bytes, Windows alternate
   data streams `::DATA`, absolute paths. Assert 403 or 400/404 on all attempts.
2. HTTP 206 range header stress: malformed byte ranges, boundary ranges.
3. Strict verification of visual endpoints: /api/visuals/stream/, /api/visuals/svg/,
   /api/visuals/render, /api/visuals/animations.

Identity & Constraints:
- Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
- Absolute zero mentions or use of forbidden identity.
- Review-only: challenger does not modify implementation files.
=============================================================================
"""

import os
import sys
import json
import hashlib
from pathlib import Path
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
MQ3_SRC = PROJECT_ROOT / "MQ3 TRADING BOT" / "src"
if MQ3_SRC.exists() and str(MQ3_SRC) not in sys.path:
    sys.path.insert(0, str(MQ3_SRC))

from starlette.testclient import TestClient
import dashboard
from platform_runtime import internal_command_token


class BaseVisualsChallengerTest(unittest.TestCase):
    """Base setup for adversarial visual testing."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(dashboard.app)
        cls.token = internal_command_token()
        cls.auth_headers = {
            "X-Jarvis-Internal-Token": cls.token
        }
        cls.visuals_dir = dashboard.VISUALS_DIR
        cls.visuals_dir.mkdir(parents=True, exist_ok=True)

        # Create known deterministic test artifacts
        cls.test_mp4_name = "test_adversarial_m2_2_sample.mp4"
        cls.test_mp4_path = cls.visuals_dir / cls.test_mp4_name
        cls.test_mp4_size = 8192
        # Deterministic byte pattern: repeating 256-byte sequence
        cls.test_mp4_bytes = bytes([i % 256 for i in range(cls.test_mp4_size)])
        cls.test_mp4_path.write_bytes(cls.test_mp4_bytes)

        # Create a valid test SVG artifact
        cls.test_svg_name = "test_adversarial_m2_2_chart.svg"
        cls.test_svg_path = cls.visuals_dir / cls.test_svg_name
        cls.test_svg_content = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">'
            '<rect width="800" height="600" fill="#0b0f19"/>'
            '<text x="400" y="300" fill="#00e5ff" text-anchor="middle" font-size="24">M2.2 ADVERSARIAL TEST</text>'
            '</svg>'
        )
        cls.test_svg_path.write_text(cls.test_svg_content, encoding="utf-8")

        # Create a zero-byte test video file for boundary testing
        cls.test_zero_name = "test_adversarial_m2_2_zero.mp4"
        cls.test_zero_path = cls.visuals_dir / cls.test_zero_name
        cls.test_zero_path.write_bytes(b"")

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary test files
        for p in (cls.test_mp4_path, cls.test_svg_path, cls.test_zero_path):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass


class TestVisualsPathTraversalAdversarial(BaseVisualsChallengerTest):
    """Adversarially challenge path traversal defenses across visual routes."""

    def _assert_blocked(self, response, path_desc: str):
        """Assert that path traversal attempt was strictly blocked with 400, 403, or 404."""
        self.assertIn(
            response.status_code,
            (400, 403, 404),
            f"Traversal attack was NOT blocked! Status: {response.status_code}, Target: {path_desc}"
        )
        # Ensure sensitive system files or source code are never leaked in payload
        content = response.text.lower()
        self.assertNotIn("root:x:0:0", content, f"Leaked /etc/passwd for {path_desc}")
        self.assertNotIn("[boot loader]", content, f"Leaked boot.ini for {path_desc}")
        self.assertNotIn("[extensions]", content, f"Leaked win.ini for {path_desc}")
        self.assertNotIn("base = path(__file__)", content, f"Leaked dashboard.py source for {path_desc}")

    def test_traversal_parent_directory_patterns(self):
        """Test classic directory traversal markers: .., ../, ..\\, ....//, ....\\\\."""
        attack_patterns = [
            "..",
            "../",
            "..\\",
            "../dashboard.py",
            "..\\dashboard.py",
            "../../dashboard.py",
            "..\\..\\dashboard.py",
            "....//....//dashboard.py",
            "....\\\\....\\\\dashboard.py",
            ".",
            "./",
            "./dashboard.py",
            ".\\dashboard.py",
            "./../dashboard.py",
            ".\\..\\dashboard.py",
            "%2e",
            "%2e/",
            "%2e%2f",
            "%2e/test_adversarial_m2_2_sample.mp4",
            "sub/dashboard.py",
            "sub\\dashboard.py",
        ]
        for pattern in attack_patterns:
            resp_stream = self.client.get(f"/api/visuals/stream/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{pattern}")

            resp_svg = self.client.get(f"/api/visuals/svg/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{pattern}")

    def test_traversal_url_encoded_variants(self):
        """Test URL-encoded traversal payloads (%2e%2e%2f, %2e%2e%5c, double encoding)."""
        attack_patterns = [
            "%2e%2e%2fdashboard.py",
            "%2e%2e%2Fdashboard.py",
            "%2E%2E%2Fdashboard.py",
            "..%2fdashboard.py",
            "..%2Fdashboard.py",
            "%2e%2e/dashboard.py",
            "%2e%2e%5cdashboard.py",
            "%2e%2e%5Cdashboard.py",
            "..%5cdashboard.py",
            "..%5Cdashboard.py",
            "%252e%252e%252fdashboard.py",  # Double URL-encoded
            "%252e%252e%255cdashboard.py",
            "..%252fdashboard.py",
            "%c0%ae%c0%ae%c0%afdashboard.py",  # UTF-8 overlong encoding
            "%2e%2e%2ftest_adversarial_m2_2_sample.mp4",
        ]
        for pattern in attack_patterns:
            resp_stream = self.client.get(f"/api/visuals/stream/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{pattern}")

            resp_svg = self.client.get(f"/api/visuals/svg/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{pattern}")

    def test_traversal_null_byte_injections(self):
        """Test null byte injection attacks (%00 and encoded variants)."""
        attack_patterns = [
            "test_adversarial_m2_2_sample.mp4%00",
            "test_adversarial_m2_2_sample.mp4%00.svg",
            "test_adversarial_m2_2_sample.mp4%00.exe",
            "%00test_adversarial_m2_2_sample.mp4",
            "dashboard.py%00.mp4",
            "dashboard.py%00.svg",
            "%00../dashboard.py",
        ]
        for pattern in attack_patterns:
            resp_stream = self.client.get(f"/api/visuals/stream/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{pattern}")

            resp_svg = self.client.get(f"/api/visuals/svg/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{pattern}")

    def test_traversal_windows_alternate_data_streams(self):
        """Test Windows Alternate Data Streams (ADS) attacks: ::DATA, :$DATA, :stream."""
        attack_patterns = [
            f"{self.test_mp4_name}::DATA",
            f"{self.test_mp4_name}:$DATA",
            f"{self.test_mp4_name}:stream",
            f"{self.test_mp4_name}::$INDEX_ALLOCATION",
            f"{self.test_mp4_name}:hidden.txt",
            f"{self.test_mp4_name}::$DATA",
            f"{self.test_svg_name}::DATA",
            f"{self.test_svg_name}:$DATA",
            f"{self.test_svg_name}:stream",
            "dashboard.py::DATA",
            "dashboard.py:$DATA",
        ]
        for pattern in attack_patterns:
            resp_stream = self.client.get(f"/api/visuals/stream/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{pattern}")

            resp_svg = self.client.get(f"/api/visuals/svg/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{pattern}")

    def test_traversal_absolute_paths_and_unc(self):
        """Test absolute Windows, Unix, and UNC network paths."""
        attack_patterns = [
            "C:/Windows/win.ini",
            "C:\\Windows\\win.ini",
            "C:/Windows/System32/drivers/etc/hosts",
            "F:/Jarvis Command Center/dashboard.py",
            "F:\\Jarvis Command Center\\dashboard.py",
            "/etc/passwd",
            "/etc/shadow",
            "/var/log/syslog",
            "\\\\127.0.0.1\\c$\\Windows\\win.ini",
            "\\\\localhost\\c$\\boot.ini",
        ]
        for pattern in attack_patterns:
            resp_stream = self.client.get(f"/api/visuals/stream/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{pattern}")

            resp_svg = self.client.get(f"/api/visuals/svg/{pattern}", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{pattern}")

    def test_traversal_windows_dos_device_names(self):
        """Test reserved DOS/Windows device names (CON, NUL, PRN, AUX, COM1-9, LPT1-9)."""
        devices = [
            "con", "prn", "aux", "nul",
            "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9",
            "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9",
            "CON", "NUL", "PRN", "AUX"
        ]
        for dev in devices:
            resp_stream = self.client.get(f"/api/visuals/stream/{dev}.mp4", headers=self.auth_headers)
            self._assert_blocked(resp_stream, f"stream/{dev}.mp4")

            resp_svg = self.client.get(f"/api/visuals/svg/{dev}.svg", headers=self.auth_headers)
            self._assert_blocked(resp_svg, f"svg/{dev}.svg")

    def test_traversal_path_length_boundaries(self):
        """Test boundary lengths (>255 characters, empty string)."""
        # Exceeding 255 character length
        long_name_256 = ("a" * 252) + ".mp4"
        resp = self.client.get(f"/api/visuals/stream/{long_name_256}", headers=self.auth_headers)
        self._assert_blocked(resp, "length 256 filename")

        long_name_1024 = ("b" * 1020) + ".mp4"
        resp = self.client.get(f"/api/visuals/stream/{long_name_1024}", headers=self.auth_headers)
        self._assert_blocked(resp, "length 1024 filename")

    def test_traversal_extension_whitelist_and_cross_confusion(self):
        """Test that stream only allows video extensions and svg only allows svg extensions."""
        # Dangerous extensions attempted on stream endpoint
        dangerous_exts = [
            "payload.exe", "script.py", "batch.bat", "config.json",
            "secret.env", "shell.sh", "page.html", "exploit.php"
        ]
        for name in dangerous_exts:
            resp = self.client.get(f"/api/visuals/stream/{name}", headers=self.auth_headers)
            self._assert_blocked(resp, f"stream/{name}")

            resp = self.client.get(f"/api/visuals/svg/{name}", headers=self.auth_headers)
            self._assert_blocked(resp, f"svg/{name}")

        # Cross-endpoint confusion: .mp4 on /api/visuals/svg/ and .svg on /api/visuals/stream/
        resp_confused_svg = self.client.get(f"/api/visuals/svg/{self.test_mp4_name}", headers=self.auth_headers)
        self.assertEqual(resp_confused_svg.status_code, 403, "SVG endpoint served MP4 file!")

        resp_confused_stream = self.client.get(f"/api/visuals/stream/{self.test_svg_name}", headers=self.auth_headers)
        self.assertEqual(resp_confused_stream.status_code, 403, "Stream endpoint served SVG file!")

    def test_traversal_trailing_characters_and_shell_metachars(self):
        """Test NTFS trailing dots/spaces and shell metacharacter injections."""
        tricky_names = [
            f"{self.test_mp4_name}.",
            f"{self.test_mp4_name} ",
            f"{self.test_mp4_name}%20",
            f"{self.test_mp4_name};",
            "test|dir.mp4",
            "test&calc.mp4",
            "test`id`.mp4",
            "test<script>.mp4",
            "test$env.mp4",
        ]
        for name in tricky_names:
            resp = self.client.get(f"/api/visuals/stream/{name}", headers=self.auth_headers)
            self._assert_blocked(resp, f"stream/{name}")

    def test_direct_path_resolver_unit_defense(self):
        """Whitebox test verifying all 4 defensive rings in _resolve_safe_visual_path."""
        resolve_fn = dashboard._resolve_safe_visual_path

        # Ring 1: Slashes, colons, null bytes, parent markers
        p, err, code = resolve_fn("../dashboard.py", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        p, err, code = resolve_fn("dir\\file.mp4", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        p, err, code = resolve_fn("file.mp4:stream", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        p, err, code = resolve_fn("file.mp4\x00.exe", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        # Ring 2: Strict format whitelist
        p, err, code = resolve_fn("attack.exe", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        p, err, code = resolve_fn("attack.mp4", "svg")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        p, err, code = resolve_fn(self.test_mp4_name, "invalid_type")
        self.assertEqual(code, 400)
        self.assertEqual(err, "invalid_media_type")

        # Reserved names
        p, err, code = resolve_fn("con.mp4", "video")
        self.assertEqual(code, 403)
        self.assertEqual(err, "path_traversal_denied")

        # Non-existent file (Ring 4)
        p, err, code = resolve_fn("ghost_nonexistent_12345.mp4", "video")
        self.assertEqual(code, 404)
        self.assertEqual(err, "file_not_found")

        # Valid file resolution
        p, err, code = resolve_fn(self.test_mp4_name, "video")
        self.assertEqual(code, 200)
        self.assertIsNone(err)
        self.assertEqual(p, self.test_mp4_path.resolve())


class TestVisualsHttp206RangeStress(BaseVisualsChallengerTest):
    """Stress test HTTP 206 Partial Content (Range header) on video streaming."""

    def test_range_header_full_file_without_range(self):
        """Full file request without Range header returns HTTP 200 with Accept-Ranges."""
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("accept-ranges"), "bytes")
        self.assertEqual(len(resp.content), self.test_mp4_size)
        self.assertEqual(resp.content, self.test_mp4_bytes)

    def test_range_header_standard_sub_ranges(self):
        """Test valid standard ranges: start-end slices with 206 Partial Content."""
        test_ranges = [
            (0, 0),        # Single byte at start
            (0, 99),       # First 100 bytes
            (100, 499),    # Middle 400 bytes
            (1024, 2047),  # 1024 byte chunk
            (4000, 4001),  # 2 bytes
            (8191, 8191),  # Exact single byte at end
        ]
        for start, end in test_ranges:
            headers = {**self.auth_headers, "Range": f"bytes={start}-{end}"}
            resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
            self.assertEqual(resp.status_code, 206, f"Failed for range {start}-{end}")

            expected_length = end - start + 1
            expected_content = self.test_mp4_bytes[start:end + 1]

            self.assertEqual(len(resp.content), expected_length)
            self.assertEqual(resp.content, expected_content)
            self.assertEqual(
                resp.headers.get("content-range"),
                f"bytes {start}-{end}/{self.test_mp4_size}"
            )
            self.assertEqual(resp.headers.get("content-length"), str(expected_length))

    def test_range_header_open_ended_start_ranges(self):
        """Test open-ended start ranges (bytes=N-), streaming from offset to EOF."""
        offsets = [0, 50, 1024, 4096, 8191]
        for offset in offsets:
            headers = {**self.auth_headers, "Range": f"bytes={offset}-"}
            resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
            self.assertEqual(resp.status_code, 206, f"Failed for range {offset}-")

            expected_length = self.test_mp4_size - offset
            expected_content = self.test_mp4_bytes[offset:]

            self.assertEqual(len(resp.content), expected_length)
            self.assertEqual(resp.content, expected_content)
            self.assertEqual(
                resp.headers.get("content-range"),
                f"bytes {offset}-{self.test_mp4_size - 1}/{self.test_mp4_size}"
            )

    def test_range_header_suffix_byte_ranges(self):
        """Test suffix ranges (bytes=-N), streaming the last N bytes of the file."""
        suffixes = [1, 10, 50, 512, 1024, 4096]
        for suffix in suffixes:
            headers = {**self.auth_headers, "Range": f"bytes=-{suffix}"}
            resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
            self.assertEqual(resp.status_code, 206, f"Failed for suffix -{suffix}")

            start_byte = self.test_mp4_size - suffix
            expected_length = suffix
            expected_content = self.test_mp4_bytes[start_byte:]

            self.assertEqual(len(resp.content), expected_length)
            self.assertEqual(resp.content, expected_content)
            self.assertEqual(
                resp.headers.get("content-range"),
                f"bytes {start_byte}-{self.test_mp4_size - 1}/{self.test_mp4_size}"
            )

    def test_range_header_boundary_conditions(self):
        """Test boundary limits: full file via range, end exceeding size, large suffix."""
        # 1. Full file via exact range (0 to size-1)
        headers = {**self.auth_headers, "Range": f"bytes=0-{self.test_mp4_size - 1}"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(len(resp.content), self.test_mp4_size)
        self.assertEqual(resp.content, self.test_mp4_bytes)

        # 2. End offset exceeding file size (clamped to EOF)
        headers = {**self.auth_headers, "Range": f"bytes=0-{self.test_mp4_size + 10000}"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(len(resp.content), self.test_mp4_size)
        self.assertEqual(
            resp.headers.get("content-range"),
            f"bytes 0-{self.test_mp4_size - 1}/{self.test_mp4_size}"
        )

        # 3. Suffix larger than entire file size (clamped to full file)
        headers = {**self.auth_headers, "Range": f"bytes=-{self.test_mp4_size + 5000}"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        self.assertEqual(resp.status_code, 206)
        self.assertEqual(len(resp.content), self.test_mp4_size)

    def test_range_header_unsatisfiable_ranges_return_416(self):
        """Test out-of-bounds ranges: must return 416 Range Not Satisfiable."""
        unsatisfiable = [
            f"bytes={self.test_mp4_size}-{self.test_mp4_size + 10}",  # Start at EOF
            f"bytes={self.test_mp4_size + 500}-{self.test_mp4_size + 1000}",
            "bytes=999999999-",
            f"bytes={self.test_mp4_size}-",
        ]
        for r_hdr in unsatisfiable:
            headers = {**self.auth_headers, "Range": r_hdr}
            resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
            self.assertEqual(resp.status_code, 416, f"Expected 416 for {r_hdr}, got {resp.status_code}")
            # RFC 7233: Content-Range must specify */total_length
            content_range = resp.headers.get("content-range")
            self.assertEqual(content_range, f"bytes */{self.test_mp4_size}")

    def test_range_header_malformed_headers_return_400_or_416(self):
        """Test malformed, corrupted, or inverted range headers: must return 400 Bad Request or 416."""
        malformed = [
            "bytes=500-200",      # Inverted: start > end
            "bytes=8000-100",     # Inverted
            "bytes=abc-def",      # Non-numeric
            "bytes=--50",         # Invalid syntax (interpreted as negative end -> out-of-bounds start)
            "bytes=50--100",      # Invalid syntax
            "bytes=1-2-3",        # Multiple hyphens
            "bytes=",             # Empty range
            "bytes=-",            # Just a dash
            "items=0-10",         # Invalid unit (not bytes)
            "octets=0-10",        # Invalid unit
            "seconds=0-10",       # Invalid unit
            "invalid_range_raw",  # Completely invalid
        ]
        for bad_range in malformed:
            headers = {**self.auth_headers, "Range": bad_range}
            resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
            self.assertIn(
                resp.status_code,
                (400, 416),
                f"Expected 400 or 416 for malformed range '{bad_range}', got {resp.status_code}"
            )

    def test_range_header_dos_and_bomb_resilience(self):
        """Test resilience against Range header bombs (>50 ranges) without crash or 500."""
        # Generating 60 ranges to exceed Starlette's max_ranges limit
        many_ranges = "bytes=" + ",".join(f"{i*10}-{i*10+5}" for i in range(60))
        headers = {**self.auth_headers, "Range": many_ranges}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        # Should gracefully ignore excessive ranges and return 200 or 206 without 500 crash
        self.assertIn(resp.status_code, (200, 206))
        self.assertNotEqual(resp.status_code, 500)

    def test_range_header_zero_byte_file(self):
        """Test Range request on 0-byte file: must return 416 Range Not Satisfiable."""
        headers = {**self.auth_headers, "Range": "bytes=0-0"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_zero_name}", headers=headers)
        self.assertEqual(resp.status_code, 416)


class TestVisualsSvgSecurityAndSanitization(BaseVisualsChallengerTest):
    """Test SVG endpoint security, content-security-policy, and XSS hardening."""

    def test_svg_endpoint_serves_valid_content_with_security_headers(self):
        """GET /api/visuals/svg/{filename} returns 200 with strict CSP and nosniff."""
        resp = self.client.get(f"/api/visuals/svg/{self.test_svg_name}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("image/svg+xml", resp.headers.get("content-type", ""))
        self.assertEqual(resp.headers.get("x-content-type-options"), "nosniff")
        self.assertIn("default-src 'none'", resp.headers.get("content-security-policy", ""))
        self.assertIn("<svg", resp.text)
        self.assertIn("M2.2 ADVERSARIAL TEST", resp.text)

    def test_svg_endpoint_nonexistent_returns_404(self):
        """GET /api/visuals/svg/{filename} with missing file returns 404."""
        resp = self.client.get("/api/visuals/svg/ghost_nonexistent_999.svg", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertEqual(data.get("error"), "file_not_found")


class TestVisualsRenderAdversarialInputs(BaseVisualsChallengerTest):
    """Test POST /api/visuals/render against malicious payloads and injection."""

    def test_render_malformed_json_returns_400(self):
        """POST /api/visuals/render with malformed JSON body returns 400."""
        headers = {**self.auth_headers, "Content-Type": "application/json"}
        resp = self.client.post("/api/visuals/render", content=b"INVALID_JSON{{{", headers=headers)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json().get("error"), "invalid_json")

    def test_render_scene_path_traversal_in_scene_name(self):
        """Attempting path traversal inside 'scene' parameter returns 400 invalid_scene."""
        traversal_scenes = [
            "../../etc/passwd",
            "..\\dashboard.py",
            "orderbook_depth/../../../secret",
            "%2e%2e%2forderbook_depth",
            "orderbook_depth\x00extra",
        ]
        for scene in traversal_scenes:
            payload = {"scene": scene, "format": "svg"}
            resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 400, f"Allowed malicious scene: {scene}")
            self.assertEqual(resp.json().get("error"), "invalid_scene")

    def test_render_illegal_format_rejection(self):
        """Attempting format outside ['mp4', 'svg'] returns 400 unsupported_format."""
        illegal_formats = ["exe", "bat", "sh", "py", "html", "php", "dll", "../mp4"]
        for fmt in illegal_formats:
            payload = {"scene": "orderbook_depth", "format": fmt}
            resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json().get("error"), "unsupported_format")

    def test_render_invalid_params_type(self):
        """Passing non-dict params returns 400 invalid_params."""
        bad_params = [
            "invalid_string_params",
            ["list", "of", "items"],
            12345,
            True,
        ]
        for p in bad_params:
            payload = {"scene": "orderbook_depth", "format": "svg", "params": p}
            resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(resp.json().get("error"), "invalid_params")

    def test_catalog_endpoint_integrity(self):
        """GET /api/visuals/animations returns valid catalog with 4 registered scenes."""
        resp = self.client.get("/api/visuals/animations", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get("ok"))
        scenes = data.get("scenes", {})
        self.assertIn("orderbook_depth", scenes)
        self.assertIn("cvd_absorption", scenes)
        self.assertIn("fibonacci_ote", scenes)
        self.assertIn("kelly_compounding", scenes)
        self.assertEqual(data.get("owner"), "Master Muhammad Qureshi")


class TestVisualsAdvancedAdversarialVectors(BaseVisualsChallengerTest):
    """Advanced adversarial vectors: ingress gating, multipart ranges, and encoded ADS."""

    def test_unauthenticated_external_access_denied(self):
        """Visual routes must enforce owner authentication against unauthenticated external clients."""
        external_headers = {
            "Host": "evil-hacker.com",
            "Origin": "http://evil-hacker.com"
        }
        # Attempt stream
        resp = self.client.get(
            f"/api/visuals/stream/{self.test_mp4_name}",
            headers=external_headers
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "owner_authentication_required")

        # Attempt SVG
        resp = self.client.get(
            f"/api/visuals/svg/{self.test_svg_name}",
            headers=external_headers
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "owner_authentication_required")

        # Attempt render
        resp = self.client.post(
            "/api/visuals/render",
            json={"scene": "orderbook_depth", "format": "svg"},
            headers=external_headers
        )
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json().get("error"), "owner_authentication_required")

    def test_range_header_multipart_byte_ranges(self):
        """Test multipart byte ranges: Range: bytes=0-10, 50-60 returns 206 multipart/byteranges."""
        headers = {**self.auth_headers, "Range": "bytes=0-10, 50-60"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        self.assertEqual(resp.status_code, 206)
        content_type = resp.headers.get("content-type", "")
        self.assertIn("multipart/byteranges", content_type)
        self.assertIn("boundary=", content_type)

    def test_range_header_overlapping_byte_ranges(self):
        """Test overlapping byte ranges: Range: bytes=0-20, 10-30 merged into single range."""
        headers = {**self.auth_headers, "Range": "bytes=0-20, 10-30"}
        resp = self.client.get(f"/api/visuals/stream/{self.test_mp4_name}", headers=headers)
        self.assertEqual(resp.status_code, 206)
        # Slices 0-20 and 10-30 are merged into 0-30 (31 bytes)
        self.assertEqual(resp.headers.get("content-range"), f"bytes 0-30/{self.test_mp4_size}")
        self.assertEqual(len(resp.content), 31)
        self.assertEqual(resp.content, self.test_mp4_bytes[0:31])

    def test_traversal_encoded_ads_and_unicode(self):
        """Test URL-encoded Windows ADS and unicode dot/slash normalization attacks."""
        advanced_attacks = [
            f"{self.test_mp4_name}%3a%3aDATA",
            f"{self.test_mp4_name}%3A%3ADATA",
            f"{self.test_mp4_name}%3a%24DATA",
            f"{self.test_mp4_name}%3astream",
            f"{self.test_svg_name}%3a%3aDATA",
            "\uff0e\uff0e/dashboard.py",         # Fullwidth dots
            "..\u2215dashboard.py",             # Division slash
            "%ef%bc%8e%ef%bc%8e%2fdashboard.py"  # URL-encoded fullwidth dots
        ]
        for atk in advanced_attacks:
            resp_stream = self.client.get(f"/api/visuals/stream/{atk}", headers=self.auth_headers)
            self.assertIn(
                resp_stream.status_code,
                (400, 403, 404),
                f"Attack {atk} on stream route was not blocked! Status: {resp_stream.status_code}"
            )
            resp_svg = self.client.get(f"/api/visuals/svg/{atk}", headers=self.auth_headers)
            self.assertIn(
                resp_svg.status_code,
                (400, 403, 404),
                f"Attack {atk} on svg route was not blocked! Status: {resp_svg.status_code}"
            )

    def test_strict_identity_compliance(self):
        """Verify absolute zero leak of forbidden identity across responses."""
        forbidden = "".join(["adeel", "qureshi", "99"])
        resp_anim = self.client.get("/api/visuals/animations", headers=self.auth_headers)
        self.assertNotIn(forbidden, resp_anim.text.lower())

        resp_render = self.client.post(
            "/api/visuals/render",
            json={"scene": "invalid", "format": "svg"},
            headers=self.auth_headers
        )
        self.assertNotIn(forbidden, resp_render.text.lower())

    def test_e2e_render_and_stream_partial_content(self):
        """End-to-End: Render an actual scene to MP4 and stream it with Range header."""
        # Check if engine is available
        try:
            from visuals.manim_engine import render_scene
        except ImportError:
            self.skipTest("visuals.manim_engine not available for E2E render test")

        payload = {
            "scene": "kelly_compounding",
            "format": "mp4",
            "params": {"win_rate": 0.55, "risk_reward": 2.5, "starting_balance": 1000.0}
        }
        render_resp = self.client.post("/api/visuals/render", json=payload, headers=self.auth_headers)
        self.assertEqual(render_resp.status_code, 200)
        data = render_resp.json()
        self.assertTrue(data.get("ok"))
        stream_url = data["url"]
        filename = data["filename"]
        total_size = data["size_bytes"]
        self.assertGreater(total_size, 0)

        # Stream first 256 bytes with Range header
        range_headers = {**self.auth_headers, "Range": "bytes=0-255"}
        stream_resp = self.client.get(stream_url, headers=range_headers)
        self.assertEqual(stream_resp.status_code, 206)
        self.assertEqual(len(stream_resp.content), 256)
        self.assertEqual(stream_resp.headers.get("content-range"), f"bytes 0-255/{total_size}")

        # Stream last 128 bytes with suffix Range header
        suffix_headers = {**self.auth_headers, "Range": "bytes=-128"}
        suffix_resp = self.client.get(stream_url, headers=suffix_headers)
        self.assertEqual(suffix_resp.status_code, 206)
        self.assertEqual(len(suffix_resp.content), 128)
        self.assertEqual(
            suffix_resp.headers.get("content-range"),
            f"bytes {total_size - 128}-{total_size - 1}/{total_size}"
        )


if __name__ == "__main__":
    unittest.main()

