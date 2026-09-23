"""
cockpit/server.py
========================================================================
MQ3 Cockpit Server & API Gateway (:5050).
Restores streaming live market commentary, Big Sharks order-flow radar,
SMC trade setups, open positions display, and prop-firm equity gauges.
========================================================================
"""

import os
import sys
import logging
from pathlib import Path

# Ensure MQ3 TRADING BOT and its dashboard directory are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MQ3_ROOT = PROJECT_ROOT / "MQ3 TRADING BOT"
DASHBOARD_DIR = MQ3_ROOT / "dashboard"

if str(MQ3_ROOT) not in sys.path:
    sys.path.insert(0, str(MQ3_ROOT))
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))

# Import dashboard Flask app and components directly
import app as mq3_app

app = mq3_app.app
run_dashboard = mq3_app.run_dashboard
bot_engine = mq3_app.bot_engine
get_live_commentary = mq3_app.get_live_commentary
get_status = mq3_app.get_status
get_trade_cards = mq3_app.get_trade_cards
get_positions = getattr(mq3_app, "get_positions", get_trade_cards)
get_prop_firm = getattr(mq3_app, "get_prop_firm", None)

# Ensure route aliases are registered
rules = [rule.rule for rule in app.url_map.iter_rules()]
if "/api/positions" not in rules:
    app.add_url_rule("/api/positions", "get_positions", get_positions, methods=["GET"])
if "/api/prop_firm" not in rules and get_prop_firm is not None:
    app.add_url_rule("/api/prop_firm", "get_prop_firm", get_prop_firm, methods=["GET"])


def start_cockpit_server(host: str = "127.0.0.1", port: int = 5050, simulation_mode: bool = False):
    """Starts the MQ3 Cockpit server."""
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    run_dashboard(port=port, host=host, simulation_mode=simulation_mode)


if __name__ == "__main__":
    start_cockpit_server(port=5050)
