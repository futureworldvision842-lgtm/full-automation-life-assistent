"""
core/prompt_engineer.py — J.A.R.V.I.S. Autonomous Meta-Prompt Engineering & LLM Swarm Engine
=============================================================================================
Transforms simple operator requirements into elite, highly structured prompts that extract
maximum intelligence, clean code, and zero-hallucination outputs from any LLM:
- Local Ollama (qwen2.5:0.5b / llama3 / deepseek)
- Cloud Models (OpenCode AI Zen, Gemini, Groq, OpenAI, Hermes-3)

Features:
1. Role & Domain Inception: Injects authoritative domain expertise into system prompts.
2. Few-Shot Pattern Injection: Dynamically feeds working codebase exemplars.
3. Chain-of-Thought (CoT) Decomposition: Breaks complex goals into verifiable atomic stages.
4. AST Lint-Feedback Loop: Automatically re-prompts LLMs with syntax errors for self-refinement.
5. Invariant Enforcer: Prevents prohibited identifiers, ensures deterministic risk bounds.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sys
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent

logger = logging.getLogger("JarvisPromptEngineer")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

PROHIBITED_TOKENS = ["".join(["adeel", "qureshi", "99"])]


class PromptOptimizationStyle(str, Enum):
    AUTONOMOUS_CODE_SYNTHESIS = "autonomous_code_synthesis"
    DEEP_ANALYTICAL_REASONING = "deep_analytical_reasoning"
    QUANTITATIVE_TRADING_STRATEGY = "quantitative_trading_strategy"
    SECURITY_AUDIT_AND_SANDBOX = "security_audit_and_sandbox"
    CONVERSATIONAL_AUTHORITY = "conversational_authority"


class AutonomousPromptEngineer:
    """
    World-class Prompt Engineering Meta-Compiler.
    Turns simple operator requests into deterministic, high-yield LLM prompts.
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []

    def compile_master_prompt(
        self,
        task_description: str,
        style: PromptOptimizationStyle = PromptOptimizationStyle.AUTONOMOUS_CODE_SYNTHESIS,
        domain: str = "Systems & Quantitative Software",
        target_model: str = "auto",
        include_few_shot: bool = True
    ) -> Dict[str, str]:
        """
        Synthesizes an optimized system prompt and user directive for maximal LLM adherence.
        """
        # 1. Domain-specific Persona Framing
        role_headers = {
            PromptOptimizationStyle.AUTONOMOUS_CODE_SYNTHESIS: (
                "You are an Elite Principal Software Architect and Tool Synthesizer for J.A.R.V.I.S. "
                "You write production-grade, highly optimized, typed Python code. "
                "Your code is standalone, self-documenting, handles all edge cases, and adheres to strict AST safety."
            ),
            PromptOptimizationStyle.QUANTITATIVE_TRADING_STRATEGY: (
                "You are a Senior Quantitative Researcher and High-Frequency Strategy Architect. "
                "You specialize in Orderbook microstructure, CVD absorption, Smart Money concepts, and mathematical risk management. "
                "Constraint: FundingPips #40000294403 risk must strictly never exceed 0.75% ($750 limit) per trade."
            ),
            PromptOptimizationStyle.SECURITY_AUDIT_AND_SANDBOX: (
                "You are a Principal Cybernetic Security Auditor and AST Safety Validator. "
                "You audit code for vulnerabilities, illegal system calls, memory leaks, and sandbox escapes."
            ),
            PromptOptimizationStyle.DEEP_ANALYTICAL_REASONING: (
                "You are an Omniscient Cognitive Reasoning Engine. "
                "You analyze problems step-by-step using first principles, formal logic, and empirical data."
            ),
            PromptOptimizationStyle.CONVERSATIONAL_AUTHORITY: (
                "You are J.A.R.V.I.S., the hyper-intelligent sovereign AI assistant for Master Muhammad Qureshi. "
                "You speak with supreme confidence, elegance, and decisive authority. Zero apologies ('I am sorry' is forbidden)."
            )
        }

        system_persona = role_headers.get(style, role_headers[PromptOptimizationStyle.AUTONOMOUS_CODE_SYNTHESIS])

        # 2. Strict Invariants & Constraints Injection
        invariants = [
            "1. Output ONLY valid, executable Python code or structured JSON as requested. Do NOT include extraneous conversational filler.",
            "2. Ensure zero syntax errors (ast.parse must pass without exceptions).",
            "3. Enforce Master Muhammad Qureshi's sole sovereign authority (+923468053268, futureworldvision842@gmail.com).",
            "4. NEVER include any prohibited identifiers or unauthorized credentials.",
            "5. If writing a tool, export callable entrypoint functions with clear type hints and docstrings."
        ]

        # 3. Few-shot Pattern Formulation
        few_shot_context = ""
        if include_few_shot and style == PromptOptimizationStyle.AUTONOMOUS_CODE_SYNTHESIS:
            few_shot_context = (
                "\n### Reference Exemplar (Canonical J.A.R.V.I.S. Modular Tool Pattern):\n"
                "```python\n"
                "\"\"\"\n"
                "skills/telemetry/hardware_metrics.py — High-performance low-latency system telemetry.\n"
                "\"\"\"\n"
                "import os, psutil\n"
                "from typing import Dict, Any\n\n"
                "def get_hardware_telemetry() -> Dict[str, Any]:\n"
                "    \"\"\"Collects CPU, memory, and IOPS vitals under 10ms.\"\"\"\n"
                "    return {\n"
                "        'cpu_percent': psutil.cpu_percent(interval=None),\n"
                "        'ram_percent': psutil.virtual_memory().percent,\n"
                "        'status': 'ONLINE'\n"
                "    }\n"
                "```\n"
            )

        # 4. Multi-Stage Chain-of-Thought Prompt Construction
        compiled_user_prompt = (
            f"### OBJECTIVE:\n{task_description.strip()}\n\n"
            f"### TECHNICAL DOMAIN:\n{domain}\n\n"
            f"### MANDATORY INVARIANTS & CONSTRAINTS:\n" + "\n".join(invariants) + "\n"
            f"{few_shot_context}\n"
            f"### EXECUTION STEPS:\n"
            f"1. Deconstruct the requirements into core functional components.\n"
            f"2. Implement robust error handling and defensive fallbacks.\n"
            f"3. Provide complete, drop-in replacement code with zero placeholders.\n"
            f"4. Begin directly with the code block."
        )

        record = {
            "task": task_description[:80],
            "style": style.value,
            "domain": domain,
            "compiled_at": time.time()
        }
        self.history.append(record)

        return {
            "system_prompt": system_persona,
            "user_prompt": compiled_user_prompt,
            "style": style.value
        }

    def extract_code_block(self, llm_response: str) -> str:
        """Extracts clean python code from markdown fences or raw response."""
        code_match = re.search(r"```(?:python)?\s*([\s\S]*?)\s*```", llm_response, re.IGNORECASE)
        if code_match:
            return code_match.group(1).strip()
        return llm_response.strip()

    def validate_code_ast(self, code: str) -> Tuple[bool, Optional[str]]:
        """Validates that synthesized code is syntactically valid and free of prohibited tokens."""
        for token in PROHIBITED_TOKENS:
            if token in code:
                return False, f"Code contains prohibited identity token: {token}"
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            return False, f"SyntaxError at line {e.lineno}, offset {e.offset}: {e.msg}"
        except Exception as e:
            return False, f"AST Validation Error: {e}"

    def build_refinement_prompt(self, original_code: str, error_message: str) -> str:
        """
        Constructs an iterative self-refinement prompt providing AST error feedback to the LLM.
        """
        return (
            f"The Python code generated in your previous response produced an error during AST compilation:\n\n"
            f"### ERROR REPORT:\n{error_message}\n\n"
            f"### PREVIOUS CODE:\n```python\n{original_code}\n```\n\n"
            f"### INSTRUCTIONS FOR REFINEMENT:\n"
            f"1. Fix the exact syntax/structural issue identified above.\n"
            f"2. Maintain all required function signatures and return types.\n"
            f"3. Ensure the code remains clean, standalone, and completely bug-free.\n"
            f"4. Return the entire corrected script inside a single ```python code block."
        )

    async def execute_prompt_with_models(
        self,
        compiled_prompts: Dict[str, str],
        preferred_provider: str = "auto"
    ) -> Dict[str, Any]:
        """
        Routes the engineered prompt through the AI engine across local Ollama,
        OpenCode AI Zen, Gemini, or Hermes-3 with automatic fallback.
        """
        from ai_engine import query_ai_detailed, query_local_ollama

        sys_prompt = compiled_prompts["system_prompt"]
        usr_prompt = compiled_prompts["user_prompt"]

        # Strategy 1: Try Local Ollama first for sub-second, zero-cost response
        if preferred_provider in ("auto", "ollama"):
            try:
                res = query_local_ollama(usr_prompt, system_prompt=sys_prompt)
                if res and res.get("ok") and res.get("text"):
                    return {
                        "ok": True,
                        "provider": "ollama",
                        "model": res.get("model", "local"),
                        "raw_output": res["text"],
                        "code": self.extract_code_block(res["text"])
                    }
            except Exception as e:
                logger.debug("Local Ollama query fallback: %s", e)

        # Strategy 2: Multi-Model Cloud Fallback (OpenCode AI Zen / Gemini / Groq)
        try:
            full_prompt = f"{sys_prompt}\n\n{usr_prompt}"
            res = query_ai_detailed(full_prompt)
            if res and res.get("text"):
                return {
                    "ok": True,
                    "provider": res.get("provider", "cloud_cortex"),
                    "model": res.get("model", "hybrid"),
                    "raw_output": res["text"],
                    "code": self.extract_code_block(res["text"])
                }
        except Exception as e:
            logger.error("Cloud cortex query failed: %s", e)

        return {
            "ok": False,
            "error": "All AI providers unreachable",
            "provider": "none"
        }

    async def synthesize_skill_with_self_healing(
        self,
        skill_intent: str,
        domain: str = "System Utility",
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        End-to-End Autonomous Prompt Engineering & Self-Healing Loop:
        1. Compiles master prompt.
        2. Queries multi-model AI swarm.
        3. Extracts and tests code AST.
        4. If errors occur, feeds error back into LLM for iterative refinement.
        5. Delivers verified, clean Python skill code ready for hot-reloading.
        """
        t0 = time.time()
        prompts = self.compile_master_prompt(
            task_description=skill_intent,
            style=PromptOptimizationStyle.AUTONOMOUS_CODE_SYNTHESIS,
            domain=domain
        )

        current_prompts = prompts
        history_traces = []

        for attempt in range(1, max_retries + 1):
            logger.info("Executing Prompt Synthesis Loop (Attempt %d/%d)...", attempt, max_retries)
            llm_result = await self.execute_prompt_with_models(current_prompts)
            if not llm_result.get("ok"):
                return {"ok": False, "error": llm_result.get("error"), "attempts": attempt}

            candidate_code = llm_result.get("code", "")
            is_valid, err_msg = self.validate_code_ast(candidate_code)

            history_traces.append({
                "attempt": attempt,
                "provider": llm_result.get("provider"),
                "ast_valid": is_valid,
                "error": err_msg,
                "code_len": len(candidate_code)
            })

            if is_valid:
                duration_ms = round((time.time() - t0) * 1000, 2)
                logger.info("Code AST successfully verified in %d attempt(s) (%.2fms).", attempt, duration_ms)
                return {
                    "ok": True,
                    "skill_code": candidate_code,
                    "attempts": attempt,
                    "provider": llm_result.get("provider"),
                    "duration_ms": duration_ms,
                    "traces": history_traces
                }

            # Self-healing prompt refinement
            logger.warning("AST error detected in synthesized code: %s. Initiating self-refinement...", err_msg)
            refinement_user_prompt = self.build_refinement_prompt(candidate_code, err_msg)
            current_prompts = {
                "system_prompt": prompts["system_prompt"],
                "user_prompt": refinement_user_prompt,
                "style": prompts["style"]
            }

        return {
            "ok": False,
            "error": f"Failed to synthesize error-free code after {max_retries} attempts.",
            "traces": history_traces
        }


# Singleton accessor
_prompt_engineer_instance: Optional[AutonomousPromptEngineer] = None

def get_prompt_engineer() -> AutonomousPromptEngineer:
    global _prompt_engineer_instance
    if _prompt_engineer_instance is None:
        _prompt_engineer_instance = AutonomousPromptEngineer()
    return _prompt_engineer_instance
