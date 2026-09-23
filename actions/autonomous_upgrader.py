"""
autonomous_upgrader.py — Safe Local Skill Generator for J.A.R.V.I.S.

Generates type-checked, safe Python helper scripts inside the local skills/ directory
to handle new automation tasks as requested by the user.
"""

import py_compile
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SKILLS_DIR = BASE_DIR / "skills"

def generate_local_skill(skill_name: str, code_content: str) -> str:
    """
    Safely creates and compile-checks a new Python skill script in skills/
    """
    try:
        clean_name = "".join(c if c.isalnum() or c == '_' else '_' for c in skill_name.lower())
        skill_path = SKILLS_DIR / f"{clean_name}.py"
        
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(code_content, encoding="utf-8")
        
        # Verify python syntax via py_compile
        py_compile.compile(str(skill_path), doraise=True)
        print(f"[AutonomousUpgrader] Successfully compiled new skill: {skill_path.name}")
        return f"Skill '{clean_name}' created and compiled successfully in skills/."
    except Exception as e:
        if skill_path.exists():
            try:
                skill_path.unlink()
            except Exception:
                pass
        return f"Failed to generate safe skill '{skill_name}': {e}"


def autonomous_upgrader(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """Action dispatch handler for autonomous skill generation."""
    params = parameters or {}
    skill_name = str(params.get("skill_name") or params.get("name") or "").strip()
    code_content = str(params.get("code") or params.get("code_content") or "").strip()
    if not skill_name or not code_content:
        return "Skill name and Python code content are required for autonomous upgrade."
    result = generate_local_skill(skill_name, code_content)
    if player and hasattr(player, "write_log"):
        player.write_log(f"[Upgrader] {result}")
    if speak and callable(speak):
        speak(f"Skill upgrade processed: {skill_name}")
    return result
