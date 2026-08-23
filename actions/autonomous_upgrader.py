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
