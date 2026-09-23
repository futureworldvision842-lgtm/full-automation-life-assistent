import os
import time
import logging
import datetime
from typing import Dict, Any, Optional, Tuple, List

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

logger = logging.getLogger(__name__)

class SystemVisionControl:
    """
    Jarvis System Controller for Live Desktop Vision, Mouse/Keyboard Automation,
    Voice Hearing Telemetry, and Visual MT5 Chart Inspection.
    """

    def __init__(self, screen_dir: str = "data/screenshots"):
        self.screen_dir = screen_dir
        os.makedirs(self.screen_dir, exist_ok=True)
        self.vision_active = PIL_AVAILABLE and os.environ.get("MQ3_ENABLE_SCREEN_CAPTURE", "false").lower() == "true"
        self.mouse_control_active = PYAUTOGUI_AVAILABLE and os.environ.get("MQ3_ENABLE_DESKTOP_CONTROL", "false").lower() == "true"
        logger.info(f"SystemVisionControl: Vision Active ({self.vision_active}), PyAutoGUI Active ({self.mouse_control_active})")

    def capture_screen(self, filename: str = "live_chart_inspect.png") -> Optional[str]:
        """Captures live desktop screen for MT5 chart inspection."""
        safe_filename = os.path.basename(filename) or "live_chart_inspect.png"
        filepath = os.path.join(self.screen_dir, safe_filename)
        if self.vision_active:
            try:
                img = ImageGrab.grab()
                img.save(filepath)
                logger.info(f"[Jarvis Vision] Desktop screen captured to '{filepath}'")
                return filepath
            except Exception as e:
                logger.debug(f"[Jarvis Vision] Screen capture note: {e}")
        return None

    def move_and_click(self, x: int, y: int, button: str = "left"):
        """Automates mouse movement and click on desktop."""
        if self.mouse_control_active:
            try:
                pyautogui.moveTo(x, y, duration=0.2)
                pyautogui.click(button=button)
                logger.info(f"[Jarvis Automation] Mouse clicked at ({x}, {y})")
                return True
            except Exception as e:
                logger.debug(f"[Jarvis Automation] Mouse click note: {e}")
        return False

    def send_keyboard_shortcut(self, key_combination: List[str]):
        """Executes keyboard shortcut combination."""
        if self.mouse_control_active:
            try:
                pyautogui.hotkey(*key_combination)
                logger.info(f"[Jarvis Automation] Executed keyboard shortcut: {key_combination}")
                return True
            except Exception as e:
                logger.debug(f"[Jarvis Automation] Keyboard shortcut note: {e}")
        return False

    def listen_voice_command(self) -> Dict[str, Any]:
        """Report voice-input capability without pretending a microphone is active."""
        return {
            "status": "UNAVAILABLE",
            "voice_channel": "NOT_IMPLEMENTED",
            "last_heard": None,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
            "message": "Use the WhatsApp audio transcription pipeline for voice commands.",
        }
