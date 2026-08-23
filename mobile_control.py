"""
J.A.R.V.I.S. Mobile Remote Control
----------------------------------
A small FastAPI server so you can use owner-approved JARVIS capabilities from
your phone on the same Wi-Fi. It uses a strong private access key, mission-aware
Hermes chat, one-time approval codes for consequential commands, screenshot,
lock, volume and safely validated app launching. It exposes no raw remote shell.

Run:  python mobile_control.py     (or it's launched by start_jarvis_boot.bat)
"""
import json
import asyncio
import hmac
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
import uvicorn

BASE = Path(__file__).resolve().parent
ACCESS_TOKEN = os.getenv("JARVIS_MOBILE_TOKEN", "").strip()
PORT = 8765
_failures: dict[str, list[float]] = {}

app = FastAPI(title="JARVIS Mobile")


def _auth(req: Request) -> bool:
    if not ACCESS_TOKEN:
        return False
    client = req.client.host if req.client else "unknown"
    now = time.time()
    recent = [stamp for stamp in _failures.get(client, []) if now - stamp < 300]
    _failures[client] = recent
    if len(recent) >= 8:
        return False
    supplied = req.headers.get("X-Jarvis-Token") or req.headers.get("X-Pin") or ""
    allowed = hmac.compare_digest(supplied, ACCESS_TOKEN)
    if not allowed:
        recent.append(now)
    return allowed


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


PAGE = """<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>JARVIS Mobile</title><style>
*{box-sizing:border-box;font-family:Consolas,monospace}
body{background:#04080f;color:#19e0ff;margin:0;padding:14px}
h1{font-size:20px;text-align:center;letter-spacing:3px;text-shadow:0 0 8px #19e0ff}
.sub{text-align:center;color:#5a7a8a;font-size:11px;margin-bottom:14px}
input,textarea,button{width:100%;padding:11px;margin:5px 0;border-radius:8px;
 border:1px solid #16404f;background:#081722;color:#cfeefb;font-size:15px}
button{background:#0a2230;color:#19e0ff;border:1px solid #19e0ff;font-weight:bold;cursor:pointer}
button:active{background:#19e0ff;color:#04080f}
.row{display:flex;gap:6px}.row button{flex:1}
.card{background:#06121c;border:1px solid #11303d;border-radius:10px;padding:10px;margin-bottom:12px}
.lbl{color:#5a7a8a;font-size:11px;margin:6px 0 2px}
#out{white-space:pre-wrap;font-size:12px;color:#9fe;max-height:42vh;overflow:auto}
img{width:100%;border-radius:8px;margin-top:8px}
</style></head><body>
<h1>J.A.R.V.I.S</h1><div class=sub>OWNER-CONTROLLED MOBILE MISSION CONSOLE</div>
<div class=card id=pinbox>
 <div class=lbl>ENTER PRIVATE ACCESS KEY</div>
 <input id=pin type=password autocomplete=current-password placeholder="Access key">
 <button onclick="savePin()">UNLOCK</button>
</div>
<div id=app style=display:none>
 <div class=card>
  <div class=lbl>MISSION-AWARE JARVIS CHAT</div>
  <textarea id=ask rows=2 placeholder="Research, explain, plan or draft..."></textarea>
  <button onclick="ask()">ASK HERMES + JARVIS</button>
 </div>
 <div class=card>
  <div class=lbl>OWNER COMMAND</div>
  <input id=cmd placeholder="e.g. check all mission sites">
  <button onclick="command()">SEND TO JARVIS</button>
  <div class=lbl>Consequential actions return a one-time approval code. No hidden shell is exposed.</div>
 </div>
 <div class=card>
  <div class=lbl>OPEN APP</div>
  <input id=app_name placeholder="e.g. notepad, chrome">
  <button onclick="openApp()">OPEN</button>
 </div>
 <div class=card>
  <div class=lbl>QUICK CONTROLS</div>
  <div class=row><button onclick="q('volup')">VOL +</button><button onclick="q('voldown')">VOL -</button><button onclick="q('mute')">MUTE</button></div>
  <div class=row><button onclick="q('lock')">LOCK PC</button><button onclick="shot()">SCREENSHOT</button></div>
 </div>
 <div class=card><div class=lbl>OUTPUT</div><div id=out>Ready.</div><img id=img style=display:none></div>
</div>
<script>
let PIN=sessionStorage.getItem('pin')||'';
if(PIN){document.getElementById('pinbox').style.display='none';document.getElementById('app').style.display='block';}
function savePin(){PIN=document.getElementById('pin').value;sessionStorage.setItem('pin',PIN);
 document.getElementById('pinbox').style.display='none';document.getElementById('app').style.display='block';}
function out(t){document.getElementById('out').textContent=t;document.getElementById('img').style.display='none';}
async function post(u,b){const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json','X-Jarvis-Token':PIN},body:JSON.stringify(b||{})});const j=await r.json();if(!r.ok&&j.error)throw new Error(j.error);return j;}
async function ask(){try{out('Thinking...');const r=await post('/api/ask',{q:document.getElementById('ask').value});out(r.text||r.error);}catch(e){out(e.message);}}
async function command(){try{out('Sending...');const r=await post('/api/command',{command:document.getElementById('cmd').value});out(r.message||r.transcript||r.error||'Accepted.');}catch(e){out(e.message);}}
async function openApp(){const r=await post('/api/open',{app:document.getElementById('app_name').value});out(r.output||r.error);}
async function q(a){out(a+'...');const r=await post('/api/quick',{action:a});out(r.output||r.error);}
async function shot(){out('Capturing...');const r=await fetch('/api/screenshot',{headers:{'X-Jarvis-Token':PIN}});if(r.ok){const b=await r.blob();const i=document.getElementById('img');i.src=URL.createObjectURL(b);i.style.display='block';document.getElementById('out').textContent='Screenshot:';}else out('Failed / wrong access key');}
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


def _bridge_post(path: str, payload: dict, timeout: int = 30) -> tuple[int, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"http://127.0.0.1:8760{path}",
        data=data,
        method="POST",
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read().decode("utf-8", "replace"))
        except Exception:
            return error.code, {"ok": False, "error": "JARVIS rejected the command."}


@app.post("/api/ask")
async def api_ask(req: Request):
    if not _auth(req):
        return JSONResponse({"error": "Wrong access key"}, status_code=403)
    body = await req.json()
    q = (body.get("q") or "").strip()
    if not q:
        return {"error": "empty"}
    try:
        from memory.mission_memory import build_prompt_context
        from skills.hermes import run as run_hermes
        task = (
            "You are Muhammad Qureshi's mission-aware JARVIS. Answer accurately and concisely. "
            "This mobile chat is research-only: do not change files, run system commands, publish, spend, vote, "
            "send messages or claim external actions happened.\n\n"
            + build_prompt_context(q) + "\n\nQUESTION: " + q
        )
        text = await asyncio.to_thread(run_hermes, {"task": task})
        return {"text": text}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/command")
async def api_command(req: Request):
    if not _auth(req):
        return JSONResponse({"error": "Wrong access key"}, status_code=403)
    body = await req.json()
    command = (body.get("command") or "").strip()
    if not command:
        return {"error": "empty"}
    try:
        status, result = await asyncio.to_thread(_bridge_post, "/command", {
            "text": command,
            "source": "mobile-owner",
            "owner_id": "mobile-owner",
        }, 30)
        return JSONResponse(result, status_code=status)
    except Exception as e:
        return JSONResponse({"error": f"JARVIS command bridge unavailable: {type(e).__name__}"}, status_code=503)


@app.post("/api/open")
async def api_open(req: Request):
    if not _auth(req):
        return JSONResponse({"error": "Wrong access key"}, status_code=403)
    body = await req.json()
    app_name = (body.get("app") or "").strip()
    if not app_name:
        return {"error": "empty"}
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", app_name):
        return JSONResponse({"error": "Use an installed app name only; paths and shell syntax are blocked."}, status_code=400)
    try:
        subprocess.Popen(["powershell", "-NoProfile", "-Command", f"Start-Process '{app_name}'"])
        return {"output": f"Opening {app_name}..."}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/quick")
async def api_quick(req: Request):
    if not _auth(req):
        return JSONResponse({"error": "Wrong access key"}, status_code=403)
    body = await req.json()
    action = (body.get("action") or "").strip()
    ps = {
        "lock": "rundll32.exe user32.dll,LockWorkStation",
        "volup": "(New-Object -ComObject WScript.Shell).SendKeys([char]175)",
        "voldown": "(New-Object -ComObject WScript.Shell).SendKeys([char]174)",
        "mute": "(New-Object -ComObject WScript.Shell).SendKeys([char]173)",
    }.get(action)
    if not ps:
        return {"error": "unknown action"}
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=10)
        return {"output": f"{action} done."}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/screenshot")
def api_screenshot(req: Request):
    if not _auth(req):
        return JSONResponse({"error": "Wrong access key"}, status_code=403)
    try:
        import io
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
        except Exception:
            import pyautogui
            img = pyautogui.screenshot()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except Exception as e:
        return JSONResponse({"error": str(e)[:200]}, status_code=500)


if __name__ == "__main__":
    # Show the REAL LAN address — 0.0.0.0 is not a reachable URL from a phone.
    lan_ip = "?"
    try:
        import socket as _s
        probe = _s.socket(_s.AF_INET, _s.SOCK_DGRAM)
        probe.connect(("8.8.8.8", 80))
        lan_ip = probe.getsockname()[0]
        probe.close()
    except Exception:
        pass
    print(f"[JARVIS Mobile] PHONE URL:  http://{lan_ip}:{PORT}")
    print(f"[JARVIS Mobile] Strong access key configured: {bool(ACCESS_TOKEN)}")
    print("[JARVIS Mobile] Phone must be on the SAME Wi-Fi as this PC.")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
