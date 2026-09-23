"""
trading/ai_trader/formula_parser.py — Safe AST Formula Parser Sandbox
=============================================================================
Whitelisted mathematical Abstract Syntax Tree (AST) expression validator and
vectorized Pandas evaluator. Completely eliminates Python eval() / exec() security
vulnerabilities while providing epsilon-guarded numerical evaluation.

Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of prohibited identity. Hot wallet private key isolation.
=============================================================================
"""

import ast
import math
import logging
from typing import Dict, Any, List, Optional, Set
import numpy as np
import pandas as pd

from trading.ai_trader.qlib_factors import compute_rsi

logger = logging.getLogger("FormulaASTParser")

DANGEROUS_SUBSTRINGS: Set[str] = {
    "__", "import", "exec", "eval", "system", "builtins", "subprocess",
    "compile", "globals", "locals", "getattr", "setattr", "delattr",
    "shutil", "socket", "urllib", "requests"
}

FORBIDDEN_IDENTIFIERS: Set[str] = {
    "os", "sys", "file", "eval", "exec", "system", "subprocess",
    "builtins", "compile", "globals", "locals", "getattr", "setattr",
    "delattr", "shutil", "socket", "urllib", "requests", "lambda"
}


def _safe_div(x, y):
    x_s = pd.Series(x) if not isinstance(x, pd.Series) else x
    y_s = pd.Series(y) if not isinstance(y, pd.Series) else y
    denom = np.where(np.abs(y_s) > 1e-12, y_s, 1e-12 * np.sign(y_s + 1e-15))
    res = x_s / denom
    return res.replace([np.inf, -np.inf], 0.0).fillna(0.0)


WHITELIST_FUNCTIONS = {
    # Unary
    "Abs": lambda x: np.abs(x),
    "Sign": lambda x: np.sign(x),
    "Log": lambda x: np.log(np.maximum(x, 1e-9)),
    "Sqrt": lambda x: np.sqrt(np.maximum(x, 0.0)),
    "Neg": lambda x: -x,
    # Binary
    "Add": lambda x, y: x + y,
    "Sub": lambda x, y: x - y,
    "Mul": lambda x, y: x * y,
    "Div": _safe_div,
    "Max": lambda x, y: np.maximum(x, y),
    "Min": lambda x, y: np.minimum(x, y),
    # Time-series (x: pd.Series, d: int)
    "Ref": lambda x, d: pd.Series(x).shift(int(d)).bfill(),
    "Delta": lambda x, d: pd.Series(x) - pd.Series(x).shift(int(d)).bfill(),
    "Mean": lambda x, d: pd.Series(x).rolling(int(d), min_periods=1).mean(),
    "Std": lambda x, d: pd.Series(x).rolling(int(d), min_periods=2).std().fillna(1e-6),
    "Sum": lambda x, d: pd.Series(x).rolling(int(d), min_periods=1).sum(),
    "TsMax": lambda x, d: pd.Series(x).rolling(int(d), min_periods=1).max(),
    "TsMin": lambda x, d: pd.Series(x).rolling(int(d), min_periods=1).min(),
    "EMA": lambda x, d: pd.Series(x).ewm(span=int(d), adjust=False).mean(),
    "ZScore": lambda x, d: (pd.Series(x) - pd.Series(x).rolling(int(d), min_periods=1).mean()) / (pd.Series(x).rolling(int(d), min_periods=2).std().fillna(1e-6) + 1e-9),
    "Corr": lambda x, y, d: pd.Series(x).rolling(int(d), min_periods=2).corr(pd.Series(y)).fillna(0.0),
    "RSI": lambda x, d: compute_rsi(pd.Series(x), int(d)),
}


class FormulaASTParser:
    """
    Validates and evaluates mathematical alpha expressions via Python's AST module.
    Rejects any unapproved nodes, keywords, or non-whitelisted operations.
    """

    ALLOWED_NODE_TYPES = (
        ast.Expression,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.USub,
        ast.UAdd,
        ast.Load,
    )

    @classmethod
    def validate_expression(cls, expr_str: str) -> bool:
        """
        Validates mathematical formula expression string.
        Returns True if strictly safe and adhering to whitelisted operations.
        """
        if not expr_str or not isinstance(expr_str, str):
            return False

        # 1. Reject dangerous substrings in raw text
        lower_expr = expr_str.lower()
        for kw in DANGEROUS_SUBSTRINGS:
            if kw in lower_expr:
                return False

        # 2. Parse into AST
        try:
            tree = ast.parse(expr_str.strip(), mode="eval")
        except Exception:
            return False

        # 3. Traverse and verify every node
        for node in ast.walk(tree):
            if not isinstance(node, cls.ALLOWED_NODE_TYPES):
                return False
            # Check function calls
            if isinstance(node, ast.Call):
                func_name = node.func.id if isinstance(node.func, ast.Name) else None
                if not func_name or func_name not in WHITELIST_FUNCTIONS:
                    return False
            # Check variable names
            if isinstance(node, ast.Name):
                var = node.id
                if var.lower() in FORBIDDEN_IDENTIFIERS or any(kw in var.lower() for kw in DANGEROUS_SUBSTRINGS):
                    return False

        return True

    @classmethod
    def evaluate(cls, expr_str: str, df: pd.DataFrame) -> pd.Series:
        """
        Evaluates formula expression against market DataFrame.
        Produces finite float64 pd.Series with zero division protection.
        """
        if not cls.validate_expression(expr_str):
            raise ValueError(f"Security validation failed for expression: {expr_str}")

        tree = ast.parse(expr_str.strip(), mode="eval")

        # Build execution context from df
        context: Dict[str, Any] = {}
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                context[col] = df[col]
            elif col.capitalize() in df.columns:
                context[col] = df[col.capitalize()]

        # Precompute VWAP if referenced
        if "vwap" in expr_str.lower() or "VWAP" in expr_str:
            typical = (df["high"] + df["low"] + df["close"]) / 3.0
            cum_pv = (typical * df["volume"]).cumsum()
            cum_vol = df["volume"].cumsum()
            safe_v = np.where(cum_vol > 0, cum_vol, 1.0)
            context["vwap"] = cum_pv / safe_v
            context["VWAP"] = context["vwap"]

        # Support pre-calculated Qlib tokens
        if "KMID" in expr_str:
            safe_open = np.where(df["open"] != 0, df["open"], 1e-9)
            context["KMID"] = (df["close"] - df["open"]) / safe_open
        if "KLEN" in expr_str:
            safe_open = np.where(df["open"] != 0, df["open"], 1e-9)
            context["KLEN"] = (df["high"] - df["low"]) / safe_open
        if "VWAP_DEV" in expr_str:
            typical = (df["high"] + df["low"] + df["close"]) / 3.0
            cum_pv = (typical * df["volume"]).cumsum()
            cum_vol = df["volume"].cumsum()
            safe_v = np.where(cum_vol > 0, cum_vol, 1.0)
            vwap_s = cum_pv / safe_v
            safe_vwap = np.where(vwap_s > 0, vwap_s, 1e-9)
            context["VWAP_DEV"] = (df["close"] - vwap_s) / safe_vwap

        # Include other existing columns in df
        for col in df.columns:
            if col not in context:
                context[col] = df[col]

        def _eval_node(node):
            if isinstance(node, ast.Expression):
                return _eval_node(node.body)
            elif isinstance(node, ast.Constant):
                return float(node.value)
            elif isinstance(node, ast.Name):
                name = node.id
                if name in context:
                    return context[name]
                raise ValueError(f"Unknown variable in formula: {name}")
            elif isinstance(node, ast.BinOp):
                left = _eval_node(node.left)
                right = _eval_node(node.right)
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return _safe_div(left, right)
                raise ValueError(f"Unsupported binary operator: {type(node.op)}")
            elif isinstance(node, ast.UnaryOp):
                operand = _eval_node(node.operand)
                if isinstance(node.op, ast.USub):
                    return -operand
                elif isinstance(node.op, ast.UAdd):
                    return operand
                raise ValueError(f"Unsupported unary operator: {type(node.op)}")
            elif isinstance(node, ast.Call):
                func_name = node.func.id if isinstance(node.func, ast.Name) else None
                if func_name not in WHITELIST_FUNCTIONS:
                    raise ValueError(f"Disallowed function call: {func_name}")
                args = [_eval_node(arg) for arg in node.args]
                return WHITELIST_FUNCTIONS[func_name](*args)
            else:
                raise ValueError(f"Unsupported AST node: {type(node)}")

        raw_result = _eval_node(tree)
        if isinstance(raw_result, (int, float)):
            series = pd.Series(float(raw_result), index=df.index)
        elif isinstance(raw_result, pd.Series):
            series = raw_result
        else:
            series = pd.Series(raw_result, index=df.index)

        return series.replace([np.inf, -np.inf], 0.0).fillna(0.0)

    @classmethod
    def to_latex(cls, expr_str: str) -> str:
        """Generates pretty-printed LaTeX expression for reports and logs."""
        clean = expr_str.replace("Div", r"\frac").replace("Sub", "-").replace("Add", "+").replace("Mul", r"\times")
        return f"$${clean}$$"
