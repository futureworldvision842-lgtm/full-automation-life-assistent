"""
tests/test_dimos_spatial.py
============================
Verification for DimensionalOS (dimos) physical tools and camera gesture detector.
"""

import pytest
import numpy as np
from spatial.dimos_engine import DimosSpatialEngine, get_dimos_engine
from spatial.camera_action_detector import CameraActionDetector, get_camera_action_detector

class TestDimosEngine:
    def test_workstation_device_registration(self):
        engine = DimosSpatialEngine()
        devices = engine.list_devices()
        assert len(devices) >= 4
        dev_ids = [d["device_id"] for d in devices]
        assert "quadro_gpu_0" in dev_ids
        assert "spatial_cam_0" in dev_ids
        assert "display_center" in dev_ids

    def test_device_control_and_state(self):
        engine = DimosSpatialEngine()
        res = engine.control_device("display_center", "SET_HUD_MODE", {"mode": "CYBERPUNK_GOLD"})
        assert res["success"] is True
        assert res["hud_mode"] == "CYBERPUNK_GOLD"

        audio_res = engine.control_device("audio_comm_0", "AUDIO_BEEP")
        assert audio_res["success"] is True

    def test_hardware_vitals(self):
        engine = DimosSpatialEngine()
        vitals = engine.get_hardware_vitals()
        assert "cpu_percent" in vitals
        assert "memory_used_gb" in vitals
        assert vitals["quadro_gpu"]["name"] == "NVIDIA Quadro"
        assert vitals["active_devices_count"] >= 4


class TestCameraActionDetector:
    def test_presence_detection_on_active_frame(self):
        detector = CameraActionDetector()
        frame = detector.generate_synthetic_gesture_frame("THUMBS_UP")
        perception = detector.process_frame(frame)
        assert perception.person_present is True
        assert perception.presence_confidence > 0.3

    def test_gesture_recognition_thumbs_up(self):
        detector = CameraActionDetector()
        frame = detector.generate_synthetic_gesture_frame("THUMBS_UP")
        perception = detector.process_frame(frame)
        assert perception.gesture == "THUMBS_UP"
        assert perception.action_mapped == "YEH_DABAO_VERIFIED"
        assert perception.gesture_confidence >= 0.85

    def test_empty_frame_handling(self):
        detector = CameraActionDetector()
        empty = np.zeros((0, 0, 3), dtype=np.uint8)
        res = detector.process_frame(empty)
        assert res.person_present is False
        assert res.gesture == "NONE"

    def test_zero_prohibited_identifer(self):
        engine = DimosSpatialEngine()
        v = engine.get_hardware_vitals()
        dump = str(v).lower()
        assert "adeel" not in dump
        assert "qureshi99" not in dump
