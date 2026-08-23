"""Command-line entry point for a full owner-requested local JARVIS stop."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bootstrap.lifecycle import stop_managed_processes  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop this PC's JARVIS services without touching unrelated apps.")
    parser.add_argument("--dry-run", action="store_true", help="List matching JARVIS processes without stopping them.")
    parser.add_argument("--reason", default="owner-stop", help="Short audit reason.")
    args = parser.parse_args()
    try:
        result = stop_managed_processes(reason=args.reason, dry_run=args.dry_run)
    except Exception as error:
        print(json.dumps({"ok": False, "error": str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

