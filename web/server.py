"""
web/server.py — 3D Viral J.A.R.V.I.S. Frontend & Mobile Telemetry Server
Serves static 3D WebGL HUD and live system metrics over HTTP on port 8090.
"""

import os
import sys
import json
import time
import shutil
import psutil
import http.server
import socketserver
from pathlib import Path
from agent_hub import build_agent_hub

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = Path(__file__).resolve().parent

class JarvisTelemetryHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/api/agent-hub":
            payload = json.dumps(build_agent_hub()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/api/telemetry":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Gather telemetry data
            c_disk = shutil.disk_usage("C:/")
            e_disk = shutil.disk_usage("E:/") if os.path.exists("E:/") else None
            
            data = {
                "timestamp": time.time(),
                "system": {
                    "cpu_percent": psutil.cpu_percent(),
                    "ram_percent": psutil.virtual_memory().percent,
                    "c_drive_free_gb": round(c_disk.free / 1e9, 2),
                    "c_drive_used_gb": round(c_disk.used / 1e9, 2),
                    "e_drive_free_gb": round(e_disk.free / 1e9, 2) if e_disk else 0,
                },
                "whatsapp": {"ready": True, "port": 3200},
                "projects": [
                    {"name": "J.A.R.V.I.S. Web HUD", "url": "http://localhost:8080", "status": "ACTIVE"},
                    {"name": "One Piece Crew AI Studio", "url": "http://localhost:3142", "status": "ACTIVE"},
                    {"name": "Future World GAIGS Platform", "url": "http://localhost:5000", "status": "ACTIVE"},
                    {"name": "Masjid-e-Nabawi 3D Site", "path": "E:/Projects/GAIGS_And_Masjid_Nabawi_Backup/masjid-nabawi-main", "status": "BACKED_UP"},
                    {"name": "WhatsApp Baileys Bridge", "url": "http://localhost:3200", "status": "LINKED"}
                ]
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))
            return
        
        super().do_GET()

def run_web_server(port=8090):
    os.chdir(str(WEB_DIR))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), JarvisTelemetryHandler) as httpd:
        print(f"[JarvisWebServer] 3D Web HUD running on http://127.0.0.1:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_web_server(8090)
