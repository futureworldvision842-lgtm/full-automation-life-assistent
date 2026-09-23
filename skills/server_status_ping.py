"""Dynamically compiled skill: server_status_ping
Checks server status, verifies listening ports (8770, 8765, 5050), and reports vitals.
"""

import socket
import time
from typing import Any, Dict, List, Optional

MANIFEST = {
    "name": "server_status_ping",
    "description": "Checks server status, verifies listening ports (8770, 8765, 5050), and reports vitals.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "ports": {
                "type": "ARRAY",
                "description": "List of TCP ports to probe",
                "items": {
                    "type": "INTEGER"
                }
            },
            "host": {
                "type": "STRING",
                "description": "Target host IP or domain"
            }
        }
    }
}

def run(parameters: Optional[Dict[str, Any]] = None, player=None, speak=None) -> str:
    params = parameters or {}
    target_host = str(params.get("host") or "127.0.0.1")
    ports = params.get("ports") or [8770, 8765, 5050]
    
    report_lines = [f"[Server Status Probe] Host: {target_host}"]
    open_count = 0
    
    for port in ports:
        try:
            p_int = int(port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex((target_host, p_int))
            sock.close()
            if result == 0:
                report_lines.append(f"  - Port {p_int}: ONLINE (Active)")
                open_count += 1
            else:
                report_lines.append(f"  - Port {p_int}: STANDBY (Closed/Listening)")
        except Exception as e:
            report_lines.append(f"  - Port {port}: ERROR ({str(e)})")
            
    summary = f"Summary: {open_count}/{len(ports)} ports active on {target_host}."
    report_lines.append(summary)
    full_output = "\n".join(report_lines)
    
    if speak and callable(speak):
        speak(f"Server health check finished. {open_count} ports are responsive.")
    return full_output
