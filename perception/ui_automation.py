"""
perception/ui_automation.py — Machine-Readable Windows UI Tree Inspector
========================================================================
Uses Microsoft UI Automation & pywinauto to inspect window controls, text fields,
and buttons without sending screenshots to heavy multimodal vision models.
"""

from typing import Dict, Any, List, Optional

try:
    from pywinauto import Desktop
    import win32gui
    _HAS_PYWINAUTO = True
except Exception:
    _HAS_PYWINAUTO = False

class WindowsUIInspector:
    def __init__(self):
        pass

    def get_foreground_window_info(self) -> Dict[str, Any]:
        """Gets title, class, and bounding box of the active foreground window."""
        if not _HAS_PYWINAUTO:
            return {"error": "pywinauto/win32gui not available"}
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            cls_name = win32gui.GetClassName(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            return {
                "hwnd": hwnd,
                "title": title,
                "class_name": cls_name,
                "rect": {"left": rect[0], "top": rect[1], "right": rect[2], "bottom": rect[3]},
                "status": "ACTIVE"
            }
        except Exception as e:
            return {"error": str(e)}

    def inspect_active_window_controls(self, max_controls: int = 15) -> List[Dict[str, Any]]:
        """Extracts accessible machine-readable UI elements (buttons, inputs, labels)."""
        if not _HAS_PYWINAUTO:
            return []
        controls = []
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return []
            desktop = Desktop(backend="uia")
            window = desktop.window(handle=hwnd)
            
            for elem in window.descendants()[:max_controls]:
                try:
                    c_type = elem.element_info.control_type
                    c_name = elem.element_info.name
                    if c_name and c_type:
                        controls.append({
                            "type": c_type,
                            "name": c_name,
                            "is_enabled": elem.is_enabled()
                        })
                except Exception:
                    continue
        except Exception:
            pass
        return controls

_inspector = None
def get_ui_inspector() -> WindowsUIInspector:
    global _inspector
    if _inspector is None:
        _inspector = WindowsUIInspector()
    return _inspector

if __name__ == "__main__":
    insp = get_ui_inspector()
    fg = insp.get_foreground_window_info()
    print(f"Foreground Window: {fg.get('title')} [{fg.get('class_name')}]")
