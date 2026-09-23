"""Compatibility launcher for the single owned JARVIS supervisor."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def launch():
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.call([str(python), str(ROOT / "bootstrap/control.py"), "start", "--open"], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(launch())
