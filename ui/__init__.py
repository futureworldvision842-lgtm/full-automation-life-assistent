"""
ui package — J.A.R.V.I.S. Sovereign Ecosystem User Interfaces
-----------------------------------------------------------
Provides:
  1. Rich Terminal Dashboard (Multi-panel live visualizer & dual-mode CLI console)
  2. Compatibility layer for Desktop GUI (JarvisUI) from ui.py
"""

from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

# Export Rich Terminal Dashboard interfaces
from ui.rich_terminal_dashboard import (
    RichTerminalDashboard,
    get_terminal_dashboard_data,
    render_terminal_dashboard,
    run_terminal_dashboard,
)

# Export legacy / PyQt JarvisUI if available from root ui.py
JarvisUI = None
C = None

try:
    _root_ui_path = Path(__file__).resolve().parent.parent / "ui.py"
    if _root_ui_path.exists():
        spec = importlib.util.spec_from_file_location("_root_ui_module", str(_root_ui_path))
        if spec and spec.loader:
            _root_ui_mod = importlib.util.module_from_spec(spec)
            # Avoid re-import loops by registering in sys.modules
            if "_root_ui_module" not in sys.modules:
                sys.modules["_root_ui_module"] = _root_ui_mod
                spec.loader.exec_module(_root_ui_mod)
            JarvisUI = getattr(_root_ui_mod, "JarvisUI", None)
            C = getattr(_root_ui_mod, "C", None)
except Exception:
    JarvisUI = None
    C = None

__all__ = [
    "RichTerminalDashboard",
    "get_terminal_dashboard_data",
    "render_terminal_dashboard",
    "run_terminal_dashboard",
    "JarvisUI",
    "C",
]
