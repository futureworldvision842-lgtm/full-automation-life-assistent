"""
self_upgrade — J.A.R.V.I.S. prepares quarantined skill proposals.

Given a capability description (and optionally a GitHub repo for reference),
an online model generates a candidate skill that conforms to the plugin
interface. The code is compile-checked and stored in review_queue/upgrades.
It is never installed or activated automatically.

run_self_upgrade(capability=..., repo_url=..., name=...) -> str
"""
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


SKILLS_DIR = _base_dir() / "skills"
REVIEW_DIR = _base_dir() / "review_queue" / "upgrades"

SKILL_TEMPLATE = '''"""
Auto-generated J.A.R.V.I.S. skill: {name}
{description}
"""

MANIFEST = {{
    "name": "{name}",
    "description": "...",
    "parameters": {{"type": "OBJECT", "properties": {{}}, "required": []}},
}}


def run(parameters=None, player=None, speak=None):
    parameters = parameters or {{}}
    return "..."
'''


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", (text or "").lower()).strip("_")
    return (s or "new_skill")[:40]


def _strip_fences(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = re.sub(r"^```[a-zA-Z]*\n", "", code)
        code = re.sub(r"\n```\s*$", "", code)
    return code.strip()


def _repo_context(repo_url: str) -> str:
    """Clone shallow + read README for grounding (best-effort)."""
    try:
        dest = _base_dir() / "scratch" / "github_studies" / _slug(repo_url.split("/")[-1])
        if not dest.exists():
            subprocess.run(["git", "clone", "--depth", "1", repo_url, str(dest)],
                           capture_output=True, text=True, timeout=90)
        for cand in ("README.md", "readme.md", "README.MD"):
            p = dest / cand
            if p.exists():
                return p.read_text(encoding="utf-8", errors="ignore")[:4000]
    except Exception:
        pass
    return ""


def _validate(code: str):
    """Return (ok, error). Compile-check + ensure MANIFEST/run exist. Guardrail."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"SyntaxError: {e}"
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    has_manifest = any(
        isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "MANIFEST" for t in n.targets)
        for n in tree.body
    )
    if not has_manifest:
        return False, "missing MANIFEST"
    if "run" not in names:
        return False, "missing run() function"
    # Reject obviously destructive patterns unless clearly guarded (safety net).
    banned = ["shutil.rmtree", "os.remove(", "format(", "rd /s", "del /f", "rm -rf"]
    low = code.lower()
    for b in banned:
        if b.lower() in low:
            return False, f"contains potentially destructive call: {b}"
    return True, ""


def _gen_with_hermes(prompt: str) -> str:
    from skills.hermes import HERMES_EXE, HERMES_MODEL, HERMES_PROVIDER
    if not os.path.exists(HERMES_EXE):
        raise RuntimeError("Hermes is not installed")
    command = [
        HERMES_EXE, "-z", prompt,
        "--provider", HERMES_PROVIDER,
        "--model", HERMES_MODEL,
        "--toolsets", "clarify,memory,skills,todo",
        "--cli",
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300, cwd=os.path.dirname(HERMES_EXE))
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "Hermes generation failed")[:300])
    return _strip_fences(result.stdout or "")


def _gen(prompt: str, key: str = "") -> str:
    if key:
        try:
            from google import genai
            client = genai.Client(api_key=key)
            response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if response.text:
                return _strip_fences(response.text)
        except Exception:
            pass
    return _gen_with_hermes(prompt)


def run_self_upgrade(capability: str = "", repo_url: str = "", name: str = "", **kwargs) -> str:
    capability = (capability or "").strip()
    repo_url = (repo_url or "").strip()
    if not capability and not repo_url:
        return "Sir, tell me what capability to build (a description) or give a repo URL."

    skill_name = _slug(name) if name else _slug(capability or repo_url.split("/")[-1])

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        try:
            cfg = _base_dir() / "config" / "api_keys.json"
            key = json.loads(cfg.read_text(encoding="utf-8")).get("gemini_api_key", "")
        except Exception:
            key = ""

    repo_ctx = _repo_context(repo_url) if repo_url else ""

    base_prompt = (
        "You are J.A.R.V.I.S. writing a NEW self-contained Python skill for yourself.\n"
        "Output ONLY raw Python code — no markdown, no explanation.\n\n"
        "The file MUST define exactly this interface:\n"
        "  MANIFEST = {\"name\": \"" + skill_name + "\", \"description\": \"<clear one-line>\", "
        "\"parameters\": {\"type\": \"OBJECT\", \"properties\": {...}, \"required\": [...]}}\n"
        "  def run(parameters=None, player=None, speak=None) -> str\n\n"
        "Rules: use only the Python standard library plus 'requests' if needed. "
        "Handle errors with try/except and ALWAYS return a short human-readable string. "
        "Do NOT delete files, format drives, or run destructive shell commands. "
        "parameters is a dict; read inputs from it.\n\n"
        f"CAPABILITY TO IMPLEMENT: {capability or ('integrate useful functionality from ' + repo_url)}\n"
    )
    if repo_ctx:
        base_prompt += f"\nReference repository README (for ideas/APIs):\n{repo_ctx}\n"

    # Generate, validate, and self-repair once if needed.
    code = ""
    last_err = ""
    for attempt in range(2):
        try:
            prompt = base_prompt if attempt == 0 else (
                base_prompt + f"\nYour previous attempt was invalid: {last_err}. Fix it and output corrected full code only."
            )
            code = _gen(prompt, key)
        except Exception as e:
            return f"Self-upgrade generation error: {e}"
        ok, err = _validate(code)
        if ok:
            break
        last_err = err
    else:
        return f"Self-upgrade aborted — generated skill failed safety/validation: {last_err}"

    # Final compile-check, then quarantine as a review proposal. Generated code
    # is never written into the live skills directory automatically.
    tmp = Path(tempfile.gettempdir()) / f"_jarvis_skill_{skill_name}.py"
    tmp.write_text(code, encoding="utf-8")
    chk = subprocess.run([sys.executable, "-m", "py_compile", str(tmp)],
                         capture_output=True, text=True)
    if chk.returncode != 0:
        return f"Self-upgrade aborted — compile check failed:\n{chk.stderr.strip()[:300]}"

    proposal_id = time.strftime("%Y%m%d-%H%M%S") + "-" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:8]
    proposal_dir = REVIEW_DIR / proposal_id
    proposal_dir.mkdir(parents=True, exist_ok=False)
    dest = proposal_dir / f"{skill_name}.py"
    dest.write_text(code, encoding="utf-8")
    (proposal_dir / "proposal.json").write_text(json.dumps({
        "id": proposal_id,
        "name": skill_name,
        "capability": capability,
        "repo_url": repo_url,
        "status": "awaiting_human_review",
        "candidate": dest.name,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "checks": ["python syntax", "MANIFEST and run interface", "basic destructive-pattern scan"],
        "instruction": "Review the candidate and tests. Installation requires an explicit owner-approved code review and a separate signed change."
    }, indent=2), encoding="utf-8")
    return (
        f"Upgrade proposal {proposal_id} for '{skill_name}' was generated and compile-checked. "
        "It is quarantined in the review queue and is NOT installed. Review and explicitly approve a signed change before activation."
    )


if __name__ == "__main__":
    cap = " ".join(sys.argv[1:]) or "tell a random programming joke"
    print(run_self_upgrade(capability=cap))
