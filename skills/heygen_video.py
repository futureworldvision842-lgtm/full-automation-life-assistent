"""
heygen_video — create AI avatar videos via HeyGen for J.A.R.V.I.S.

Boss gives a script -> HeyGen renders a talking-avatar video (his content
pipeline for the Global English channel). Key lives in config/api_keys.json
as heygen_api_key. NOTE: api.heygen.com can be unreachable on some networks
(timeouts) — the skill reports that honestly instead of hanging.
"""
import json
import sys
import time
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

BASE = "https://api.heygen.com"


def _cfg():
    root = Path(__file__).resolve().parent.parent
    return json.loads((root / "config" / "api_keys.json").read_text(encoding="utf-8"))


def _key():
    return _cfg().get("heygen_api_key", "")


MANIFEST = {
    "name": "heygen_video",
    "description": (
        "Create an AI avatar video with HeyGen: Boss gives a script/text and this "
        "renders a talking-avatar video (for YouTube/shorts content). Actions: "
        "create (script -> video), status (check/render progress by video_id), "
        "check (verify API access). Use when Boss asks to make a HeyGen/avatar video."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create | status | check (default create)"},
            "script": {"type": "STRING", "description": "The narration script for the avatar to speak."},
            "video_id": {"type": "STRING", "description": "Video id for status action."},
            "orientation": {"type": "STRING", "description": "landscape (default) or portrait (shorts/reels)."},
        },
        "required": [],
    },
}


def _get(path):
    r = requests.get(BASE + path, headers={"X-Api-Key": _key()}, timeout=30)
    return r.status_code, r.json()


def _post(path, payload):
    r = requests.post(BASE + path, headers={"X-Api-Key": _key(),
                      "Content-Type": "application/json"},
                      data=json.dumps(payload), timeout=60)
    return r.status_code, r.json()


def run(parameters=None, player=None, speak=None):
    p = parameters or {}
    if requests is None:
        return "requests library missing, Sir."
    if not _key():
        return "HeyGen API key is not configured, Sir."
    action = (p.get("action") or "create").strip().lower()

    try:
        if action == "check":
            code, data = _get("/v2/avatars")
            n = len((data.get("data") or {}).get("avatars") or [])
            return f"HeyGen reachable, Sir — {n} avatars available." if code == 200 \
                   else f"HeyGen answered {code}: {str(data)[:120]}"

        if action == "status":
            vid = (p.get("video_id") or "").strip()
            if not vid:
                return "Give me the video_id, Sir."
            code, data = _get(f"/v1/video_status.get?video_id={vid}")
            d = data.get("data") or {}
            st = d.get("status")
            if st == "completed":
                return f"Video ready, Sir: {d.get('video_url')}"
            return f"Video status: {st or data} (render can take a few minutes)."

        # create
        script = (p.get("script") or "").strip()
        if not script:
            return "Give me the script to speak, Sir."
        portrait = (p.get("orientation") or "").lower().startswith("p")
        w, h = (720, 1280) if portrait else (1280, 720)

        # pick the first available avatar + a default English voice
        code, data = _get("/v2/avatars")
        avatars = (data.get("data") or {}).get("avatars") or []
        if code != 200 or not avatars:
            return f"Couldn't list HeyGen avatars (HTTP {code}), Sir."
        avatar_id = avatars[0].get("avatar_id")

        payload = {
            "video_inputs": [{
                "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                "voice": {"type": "text", "input_text": script[:1400],
                          "voice_id": "1bd001e7e50f421d891986aad5158bc8"},
            }],
            "dimension": {"width": w, "height": h},
        }
        code, data = _post("/v2/video/generate", payload)
        vid = (data.get("data") or {}).get("video_id")
        if not vid:
            return f"HeyGen create failed (HTTP {code}): {str(data)[:150]}"
        if player:
            try: player.write_log(f"HEYGEN: rendering video {vid}...")
            except Exception: pass

        # poll briefly; long renders continue in background
        for _ in range(10):
            time.sleep(15)
            c2, d2 = _get(f"/v1/video_status.get?video_id={vid}")
            dd = d2.get("data") or {}
            if dd.get("status") == "completed":
                return f"Video ready, Sir: {dd.get('video_url')}"
            if dd.get("status") == "failed":
                return f"HeyGen render failed, Sir: {str(dd.get('error'))[:120]}"
        return (f"Video {vid} is still rendering, Sir — ask me to check "
                f"heygen status with video_id {vid} in a few minutes.")

    except requests.exceptions.ConnectTimeout:
        return ("HeyGen ke servers is network se nahi khul rahe, Sir (timeout). "
                "VPN try karein ya baad mein — key configured hai, skill ready hai.")
    except Exception as e:
        return f"HeyGen error, Sir: {str(e)[:130]}"


if __name__ == "__main__":
    print(run({"action": "check"}))
