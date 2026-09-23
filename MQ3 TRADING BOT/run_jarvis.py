"""
JARVIS FULL POWER LAUNCHER — Entry point for standalone Jarvis run.
Runs JarvisFullPowerMaster.run_forever() as a separate process
alongside the main trading bot engine.
"""

import os
import sys
import logging
import argparse

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [JARVIS] %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/jarvis_full_power.log", mode='a'),
    ]
)

logger = logging.getLogger("JarvisLauncher")


def main():
    parser = argparse.ArgumentParser(description="JARVIS FULL POWER MASTER V7")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--poll", type=int, default=20, help="Heartbeat poll interval in seconds")
    parser.add_argument("--diag-only", action="store_true", help="Run one diagnostic and exit")
    args = parser.parse_args()

    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/screenshots", exist_ok=True)

    from src.jarvis_full_power_master import JarvisFullPowerMaster

    jarvis = JarvisFullPowerMaster(config_path=args.config)

    if args.diag_only:
        diag = jarvis.run_system_diagnostic()
        logger.info(f"Diagnostic complete: {diag}")
        return

    # Full continuous run
    jarvis.run_forever(poll_interval=args.poll)


if __name__ == "__main__":
    main()
