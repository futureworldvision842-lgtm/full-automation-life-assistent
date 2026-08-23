"""
video_editor — AI-powered FULL video editing for J.A.R.V.I.S.

Gemini literally WATCHES the video (Files API multimodal upload), decides the
edit like a human editor (which segments to keep, pacing, text overlays,
loudness), returns a JSON edit plan, and FFmpeg executes it locally.

Flow:  upload → Gemini analyses → edit plan JSON → ffmpeg cut/concat/overlay/
       normalize → <input>_edited.mp4

Also supports a direct `instruction` from the Boss ("remove silences and make
it punchy", "sirf best 60 seconds rakho shorts ke liye", etc.).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
MAX_UPLOAD_MB = 900          # Files API comfortably handles this
FONT = "C\\:/Windows/Fonts/arialbd.ttf"   # escaped for ffmpeg drawtext


def _base():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def _key():
    try:
        return json.loads((_base() / "config" / "api_keys.json").read_text(encoding="utf-8")).get("gemini_api_key")
    except Exception:
        return None


MANIFEST = {
    "name": "video_editor",
    "description": (
        "FULL AI video editing: Gemini watches the whole video, plans the edit "
        "(best segments, cuts, pacing, text overlays, loudness) and FFmpeg executes "
        "it — producing a finished edited video file. Use when Boss asks to edit a "
        "video, cut the boring parts, make a short/reel from a long video, add "
        "captions/overlays, or 'video edit karke do'. Pass the file path and his "
        "instruction. For simple mechanical cuts (exact trim/merge/convert) prefer "
        "podcast_editor instead."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "input": {"type": "STRING", "description": "Path to the video file to edit."},
            "instruction": {"type": "STRING", "description": "What the Boss wants, e.g. 'make a punchy 60s short with captions'. Default: tighten the video, remove dead air, keep the best parts."},
            "output": {"type": "STRING", "description": "Output path (optional; defaults to <input>_edited.mp4)."},
            "target_seconds": {"type": "INTEGER", "description": "Optional target duration in seconds (e.g. 60 for a Short)."},
        },
        "required": ["input"],
    },
}


def _run_ff(args, timeout=3600):
    r = subprocess.run([FFMPEG, "-y", *args], capture_output=True, text=True, timeout=timeout)
    return r.returncode == 0, (r.stderr or "")[-500:]


def _probe_duration(path):
    ffprobe = shutil.which("ffprobe") or FFMPEG.replace("ffmpeg", "ffprobe")
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=60)
        return float(r.stdout.strip())
    except Exception:
        return None


def _ai_plan(path, instruction, target_seconds, player=None):
    """Upload the video to Gemini and get a JSON edit plan."""
    from google import genai
    client = genai.Client(api_key=_key())

    if player:
        try: player.write_log("VIDEO: uploading to Gemini for analysis...")
        except Exception: pass

    vfile = client.files.upload(file=path)
    # Wait until the file is processed and ACTIVE.
    for _ in range(120):
        vfile = client.files.get(name=vfile.name)
        state = str(getattr(vfile, "state", "")).upper()
        if "ACTIVE" in state:
            break
        if "FAILED" in state:
            raise RuntimeError("Gemini could not process the video file.")
        time.sleep(2)

    duration = _probe_duration(path) or 0
    tgt = f" Target output duration: about {target_seconds} seconds." if target_seconds else ""
    prompt = (
        "You are a world-class video editor. Watch this video fully and produce an "
        "edit plan as STRICT JSON (no markdown). The Boss's instruction: "
        f"{instruction!r}.{tgt} Source duration: {duration:.1f}s.\n\n"
        "JSON schema:\n"
        "{\n"
        '  "keep_segments": [{"start": <sec>, "end": <sec>, "reason": "<short>"}],  // in order, non-overlapping\n'
        '  "speed": <float 0.5-2.0, 1.0 = unchanged>,\n'
        '  "text_overlays": [{"text": "<short overlay>", "start": <sec-in-OUTPUT>, "end": <sec-in-OUTPUT>}],\n'
        '  "normalize_audio": true|false,\n'
        '  "summary": "<one line what you did>"\n'
        "}\n"
        "Rules: cut dead air, stumbles, repetition; keep hooks and payoff; overlays "
        "short and punchy (<= 6 words); 0 <= start < end <= duration; if the video is "
        "already tight, keep most of it."
    )
    resp = client.models.generate_content(model="gemini-flash-latest", contents=[vfile, prompt])
    raw = (resp.text or "").strip()
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    plan = json.loads(raw)
    try:
        client.files.delete(name=vfile.name)
    except Exception:
        pass
    return plan


def _escape_drawtext(s):
    return s.replace("\\", "").replace(":", r"\:").replace("'", r"\'").replace('"', "")


def _execute(path, plan, output, player=None):
    segs = [s for s in plan.get("keep_segments", [])
            if isinstance(s, dict) and s.get("end", 0) > s.get("start", -1) >= 0]
    if not segs:
        return None, "AI returned no usable segments."
    speed = float(plan.get("speed") or 1.0)
    speed = min(2.0, max(0.5, speed))
    overlays = plan.get("text_overlays") or []
    normalize = bool(plan.get("normalize_audio"))

    # Build filter_complex: per-segment trims → concat → optional speed → overlays.
    parts, vlabels, alabels = [], [], []
    for i, s in enumerate(segs):
        parts.append(f"[0:v]trim=start={s['start']}:end={s['end']},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={s['start']}:end={s['end']},asetpts=PTS-STARTPTS[a{i}];")
        vlabels.append(f"[v{i}]"); alabels.append(f"[a{i}]")
    parts.append("".join(f"{v}{a}" for v, a in zip(vlabels, alabels))
                 + f"concat=n={len(segs)}:v=1:a=1[vc][ac];")
    vcur, acur = "[vc]", "[ac]"
    if abs(speed - 1.0) > 0.01:
        parts.append(f"{vcur}setpts=PTS/{speed}[vs];")
        parts.append(f"{acur}atempo={speed}[as];")
        vcur, acur = "[vs]", "[as]"
    for j, o in enumerate(overlays[:12]):
        txt = _escape_drawtext(str(o.get("text", ""))[:60])
        if not txt:
            continue
        st, en = float(o.get("start", 0)), float(o.get("end", 0))
        parts.append(
            f"{vcur}drawtext=fontfile='{FONT}':text='{txt}':x=(w-text_w)/2:y=h-180:"
            f"fontsize=54:fontcolor=white:borderw=4:bordercolor=black:"
            f"enable='between(t,{st},{en})'[vt{j}];")
        vcur = f"[vt{j}]"
    if normalize:
        parts.append(f"{acur}loudnorm=I=-16:TP=-1.5:LRA=11[af];")
        acur = "[af]"

    fc = "".join(parts).rstrip(";")
    ok, err = _run_ff(["-i", path, "-filter_complex", fc,
                       "-map", vcur, "-map", acur,
                       "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                       "-c:a", "aac", "-b:a", "192k", output])
    if not ok:
        return None, err
    return output, None


def run(parameters=None, player=None, speak=None):
    p = parameters or {}
    path = (p.get("input") or "").strip().strip('"')
    if not path or not os.path.exists(path):
        return f"Video file not found, Sir: {path or '(no path given)'}"
    size_mb = os.path.getsize(path) / 1e6
    if size_mb > MAX_UPLOAD_MB:
        return (f"That video is {size_mb:.0f} MB — too large to AI-analyse in one go, Sir. "
                f"Split it first (podcast_editor trim) or give me a section.")

    instruction = (p.get("instruction") or
                   "Tighten this video: remove dead air, stumbles and boring parts, "
                   "keep the hooks and best moments, natural flow.")
    output = (p.get("output") or "").strip() or None
    if not output:
        b, _ = os.path.splitext(path)
        output = b + "_edited.mp4"
    target = p.get("target_seconds")

    try:
        plan = _ai_plan(path, instruction, target, player)
    except Exception as e:
        return f"AI analysis failed, Sir: {str(e)[:120]}"

    if player:
        try: player.write_log(f"VIDEO: plan → {len(plan.get('keep_segments', []))} segments; rendering...")
        except Exception: pass

    out, err = _execute(path, plan, output, player)
    if err:
        return f"Edit render failed, Sir: {err[:150]}"
    kept = sum(s["end"] - s["start"] for s in plan.get("keep_segments", []))
    return (f"Done, Sir. Edited video saved to {out} "
            f"(~{kept:.0f}s kept). {plan.get('summary', '')}".strip())


if __name__ == "__main__":
    print(run({"input": sys.argv[1] if len(sys.argv) > 1 else ""}))
