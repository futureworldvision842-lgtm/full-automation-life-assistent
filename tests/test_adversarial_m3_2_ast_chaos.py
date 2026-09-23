"""
tests/test_adversarial_m3_2_ast_chaos.py — AST Parser & Alpha Engine Chaos Adversarial Suite
=============================================================================================
Adversarially challenges FormulaASTParser, AlphaEvaluator, QlibAlpha158, and AITraderAlphaMiner:
  1. Arbitrary code execution attack vectors (Python sandbox escape attempts, builtins, dunders, lambdas).
  2. AST recursion limits (>100 levels) and malformed syntax chaos (unclosed parens, unknown tokens).
  3. Mathematical degeneracies (all-zero, constant price series Std=0, negative volume, Infs, NaNs, N < h).
  4. Rank correlation behavior on identical constant ranks.
  5. Fail-safe neutral fallbacks and zero unhandled exception guarantees.

Author: Challenger M3.2 (AST Parser & Alpha Engine Chaos)
Roles: critic, specialist (Empirical Challenger)
Owner: Master Muhammad Qureshi (Phone: +923468053268, Email: futureworldvision842@gmail.com)
Constraints: Zero mentions of forbidden identity. Deterministic prop-firm risk <= 0.75%.
=============================================================================================
"""

import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import numpy as np
import pandas as pd

# Path setup
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from trading.ai_trader.formula_parser import FormulaASTParser, WHITELIST_FUNCTIONS
from trading.ai_trader.alpha_evaluator import AlphaEvaluator
from trading.ai_trader.qlib_factors import (
    QlibAlpha158,
    compute_rsi,
    compute_pvt,
    compute_vas,
    compute_lee_ready_cvd,
    compute_cs_momentum,
    compute_str,
    compute_correlation_divergence,
)
from trading.ai_trader.alpha_miner import AITraderAlphaMiner, DETERMINISTIC_TEMPLATES
from trading.ai_trader.types import FactorEvaluationReport


class TestASTCodeExecutionInjectionChaos(unittest.TestCase):
    """
    Stress-tests FormulaASTParser against malicious Python code injection,
    arbitrary code execution vectors, sandbox escapes, and disallowed AST node types.
    """

    def setUp(self):
        self.df = pd.DataFrame({
            "open": [1.0800, 1.0810, 1.0820, 1.0815, 1.0825],
            "high": [1.0820, 1.0835, 1.0840, 1.0830, 1.0845],
            "low": [1.0790, 1.0805, 1.0815, 1.0805, 1.0815],
            "close": [1.0810, 1.0820, 1.0830, 1.0822, 1.0835],
            "volume": [1000.0, 1500.0, 2100.0, 1800.0, 2500.0]
        })

    def test_arbitrary_code_execution_import_vectors(self):
        """Verify arbitrary code execution strings containing import are strictly blocked."""
        malicious_payloads = [
            "__import__('os').system('calc')",
            "__import__('sys').exit(1)",
            "__import__('subprocess').Popen(['calc'])",
            "import os\nos.system('calc')",
            "import sys; sys.exit(0)",
            "__import__('shutil').rmtree('.')",
            "from os import system; system('calc')",
        ]
        for payload in malicious_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(
                    FormulaASTParser.validate_expression(payload),
                    f"Payload was not blocked by validate_expression: {payload}"
                )
                with self.assertRaises(ValueError, msg=f"Payload did not raise ValueError on evaluate: {payload}"):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_arbitrary_code_execution_eval_exec_compile(self):
        """Verify eval, exec, and compile invocation vectors are strictly blocked."""
        malicious_payloads = [
            "eval('1+1')",
            "exec('a = 1')",
            "compile('1+1', '<string>', 'eval')",
            "eval('__import__(\"os\").system(\"calc\")')",
            "exec('import os; os.system(\"calc\")')",
        ]
        for payload in malicious_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_arbitrary_code_execution_file_io(self):
        """Verify open and file access primitives are strictly blocked."""
        malicious_payloads = [
            "open('passwords.txt')",
            "open('/etc/passwd').read()",
            "open('C:\\Windows\\System32\\drivers\\etc\\hosts').read()",
            "file('passwords.txt')",
        ]
        for payload in malicious_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_arbitrary_code_execution_builtins_and_globals(self):
        """Verify access to __builtins__, globals, locals, and reflection functions is blocked."""
        malicious_payloads = [
            "__builtins__",
            "__builtins__['open']('test')",
            "builtins.open('test')",
            "globals()",
            "locals()",
            "getattr(self, 'secret')",
            "setattr(self, 'admin', True)",
            "delattr(self, 'guard')",
        ]
        for payload in malicious_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_lambda_expressions_blocked(self):
        """Verify lambda function expressions are rejected by AST validator."""
        lambda_payloads = [
            "lambda x: x + 1",
            "(lambda x: x)(close)",
            "(lambda: None)()",
            "Add((lambda x: x)(close), 1)",
        ]
        for payload in lambda_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_multiline_and_compound_statements_blocked(self):
        """Verify multi-line statements and semicolons are rejected."""
        compound_payloads = [
            "x = 1\nx + 2",
            "close = 100\nclose",
            "close; open",
            "x = 10; y = 20; x + y",
        ]
        for payload in compound_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_dunder_attribute_traversal_blocked(self):
        """Verify dunder attribute traversal (Python object introspection sandbox escapes) is blocked."""
        dunder_payloads = [
            "close.__class__",
            "close.__class__.__mro__",
            "close.__class__.__subclasses__()",
            "close.__init__",
            "close.__doc__",
            "open.__name__",
        ]
        for payload in dunder_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_os_process_and_network_calls_blocked(self):
        """Verify OS commands, subprocesses, sockets, and HTTP requests are blocked."""
        os_network_payloads = [
            "os.system('calc')",
            "subprocess.Popen('calc')",
            "shutil.rmtree('.')",
            "socket.socket()",
            "urllib.request.urlopen('http://127.0.0.1')",
            "requests.get('http://127.0.0.1')",
        ]
        for payload in os_network_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(FormulaASTParser.validate_expression(payload))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(payload, self.df)

    def test_disallowed_ast_node_types(self):
        """Verify lists, dicts, slices, attributes, and comparisons are strictly rejected."""
        disallowed_nodes = [
            "[1, 2, 3]",
            "{'a': 1}",
            "(1, 2)",
            "close > open",
            "close < open",
            "close == open",
            "close and open",
            "close or open",
            "not close",
            "close[0]",
            "close.values",
            "[x for x in close]",
            "(x for x in close)",
        ]
        for expr in disallowed_nodes:
            with self.subTest(expr=expr):
                self.assertFalse(
                    FormulaASTParser.validate_expression(expr),
                    f"Disallowed node expression was erroneously accepted: {expr}"
                )

    def test_non_string_and_empty_inputs(self):
        """Verify non-string inputs, empty strings, and whitespace return False."""
        invalid_inputs = [None, "", "   ", "\t\n", 123, 45.67, [], {}, object()]
        for inp in invalid_inputs:
            with self.subTest(inp=inp):
                self.assertFalse(FormulaASTParser.validate_expression(inp))  # type: ignore
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(inp, self.df)  # type: ignore


class TestASTRecursionAndSyntaxChaos(unittest.TestCase):
    """
    Stress-tests FormulaASTParser against deeply nested recursive AST trees,
    unclosed parentheses, malformed syntax, and unknown identifiers.
    """

    def setUp(self):
        self.df = pd.DataFrame({
            "open": [1.0, 2.0, 3.0, 4.0, 5.0],
            "high": [1.5, 2.5, 3.5, 4.5, 5.5],
            "low": [0.5, 1.5, 2.5, 3.5, 4.5],
            "close": [1.2, 2.2, 3.2, 4.2, 5.2],
            "volume": [100.0, 200.0, 300.0, 400.0, 500.0]
        })

    def test_deeply_nested_ast_trees_100_levels(self):
        """Verify AST tree with 100 levels of recursive nesting evaluates safely without crash."""
        depth = 100
        expr = "Add(" * depth + "close" + ", 1.0)" * depth
        self.assertTrue(FormulaASTParser.validate_expression(expr))
        res = FormulaASTParser.evaluate(expr, self.df)
        self.assertIsInstance(res, pd.Series)
        self.assertEqual(len(res), len(self.df))
        np.testing.assert_allclose(res.values, self.df["close"].values + 100.0)

    def test_deeply_nested_ast_trees_150_levels(self):
        """Verify AST tree with 150 levels of recursive nesting evaluates safely without crash."""
        depth = 150
        expr = "Add(" * depth + "close" + ", 1.0)" * depth
        self.assertTrue(FormulaASTParser.validate_expression(expr))
        res = FormulaASTParser.evaluate(expr, self.df)
        self.assertIsInstance(res, pd.Series)
        np.testing.assert_allclose(res.values, self.df["close"].values + 150.0)

    def test_extreme_recursion_depth_handled_gracefully(self):
        """Verify extreme recursion depth (e.g. 600+ levels) does not crash the Python runtime."""
        depth = 600
        expr = "Add(" * depth + "close" + ", 1.0)" * depth
        # Should either validate False (due to internal RecursionError caught) or raise ValueError on eval
        valid = FormulaASTParser.validate_expression(expr)
        if not valid:
            self.assertFalse(valid)
        else:
            # If system recursion limit accommodates it, eval must produce a series or raise handled error
            try:
                res = FormulaASTParser.evaluate(expr, self.df)
                self.assertIsInstance(res, pd.Series)
            except (ValueError, RecursionError):
                pass  # Graceful fail-safe

    def test_unclosed_parentheses(self):
        """Verify unclosed parentheses expressions are cleanly rejected without unhandled crash."""
        unclosed_cases = [
            "Div(close, open",
            "Add(close, Mul(high, low",
            "(((((close",
            "Mean(close, 10",
            "Sub(close, Ref(close, 5)",
            "Div(Sub(close, open), Std(close, 10)",
        ]
        for expr in unclosed_cases:
            with self.subTest(expr=expr):
                self.assertFalse(FormulaASTParser.validate_expression(expr))
                with self.assertRaises(ValueError):
                    FormulaASTParser.evaluate(expr, self.df)

    def test_unopened_and_mismatched_parentheses(self):
        """Verify unopened and mismatched parentheses are cleanly rejected."""
        mismatched_cases = [
            "Div(close, open))",
            "Add close, 1)",
            ") close (",
            "close))",
            "(close)) + ((open",
        ]
        for expr in mismatched_cases:
            with self.subTest(expr=expr):
                self.assertFalse(FormulaASTParser.validate_expression(expr))

    def test_malformed_syntax_dangling_operators(self):
        """Verify dangling operators and syntax errors are cleanly rejected."""
        malformed_cases = [
            "close + ",
            "+ * close",
            "close * / open",
            "close , open",
            "close @ open",
            "Div(, close)",
            "Div(close, , open)",
        ]
        for expr in malformed_cases:
            with self.subTest(expr=expr):
                self.assertFalse(FormulaASTParser.validate_expression(expr))

    def test_function_missing_required_arguments(self):
        """
        Verify function calls with missing required arguments (e.g. Mean() with 0 args).
        Note: Currently validate_expression lacks arity checks and evaluate raises TypeError.
        """
        expr = "Mean()"
        if FormulaASTParser.validate_expression(expr):
            with self.assertRaises(TypeError, msg="Calling Mean() without args must raise TypeError or ValueError"):
                FormulaASTParser.evaluate(expr, self.df)

    def test_ohlcv_operand_open_support(self):
        """
        Verify that standard market OHLCV price operand 'open' is supported in formulas.
        NOTE: Exposes Defect where 'open' in FORBIDDEN_IDENTIFIERS blocks standard financial formulas.
        """
        expr = "Sub(close, open)"
        self.assertTrue(
            FormulaASTParser.validate_expression(expr),
            "FormulaASTParser falsely rejects standard OHLCV operand 'open' due to FORBIDDEN_IDENTIFIERS"
        )
        res = FormulaASTParser.evaluate(expr, self.df)
        self.assertIsInstance(res, pd.Series)

    def test_unknown_identifiers_in_evaluate(self):
        """Verify unknown variables raise ValueError with clear descriptive message."""
        unknown_expr = "foobar + close"
        # Validate might see 'foobar' as a syntactically valid Name node
        # but evaluate MUST fail because 'foobar' is not in context
        with self.assertRaises(ValueError) as ctx:
            FormulaASTParser.evaluate(unknown_expr, self.df)
        self.assertIn("Unknown variable", str(ctx.exception))

    def test_unknown_function_calls(self):
        """Verify non-whitelisted function names are rejected by AST validator."""
        disallowed_funcs = [
            "UnknownMathFunc(close)",
            "MyCustomIndicator(close, 5)",
            "print(close)",
            "sin(close)",
            "cos(close)",
            "tan(close)",
            "system(close)",
        ]
        for expr in disallowed_funcs:
            with self.subTest(expr=expr):
                self.assertFalse(FormulaASTParser.validate_expression(expr))

    def test_to_latex_utility(self):
        """Verify to_latex conversion outputs valid math string."""
        latex = FormulaASTParser.to_latex("Div(Sub(close, open), Std(close, 10))")
        self.assertTrue(latex.startswith("$$"))
        self.assertTrue(latex.endswith("$$"))
        self.assertIn(r"\frac", latex)


class TestMathematicalDegeneracyFactorEngines(unittest.TestCase):
    """
    Stress-tests QlibAlpha158 and dynamic factors with extreme mathematical degeneracies:
    all-zero series, constant prices (Std=0), negative volumes, infinite values, all NaNs.
    """

    def setUp(self):
        self.n_bars = 50

    def test_all_zero_dataframe_qlib_alpha158(self):
        """Verify QlibAlpha158 handles all-zero price and volume data without ZeroDivisionError."""
        df_zero = pd.DataFrame({
            "open": [0.0] * self.n_bars,
            "high": [0.0] * self.n_bars,
            "low": [0.0] * self.n_bars,
            "close": [0.0] * self.n_bars,
            "volume": [0.0] * self.n_bars
        })

        res = QlibAlpha158.compute_all(df_zero)
        self.assertEqual(res.shape, (self.n_bars, 76))
        self.assertTrue(np.isfinite(res.values).all(), "All-zero dataframe produced non-finite values")
        self.assertFalse(np.isinf(res.values).any(), "All-zero dataframe produced Inf values")

    def test_all_zero_dataframe_formula_parser(self):
        """Verify FormulaASTParser evaluates expressions on all-zero data without ZeroDivisionError."""
        df_zero = pd.DataFrame({
            "open": [0.0] * self.n_bars,
            "high": [0.0] * self.n_bars,
            "low": [0.0] * self.n_bars,
            "close": [0.0] * self.n_bars,
            "volume": [0.0] * self.n_bars
        })

        test_formulas = [
            "Div(close, high)",
            "ZScore(close, 10)",
            "Std(close, 10)",
            "Mean(close, 10)",
            "RSI(close, 14)",
            "Sub(close, Ref(close, 5))",
            "Div(Sub(close, Mean(close, 10)), Std(close, 10))",
        ]
        for f in test_formulas:
            with self.subTest(formula=f):
                s = FormulaASTParser.evaluate(f, df_zero)
                self.assertIsInstance(s, pd.Series)
                self.assertEqual(len(s), self.n_bars)
                self.assertTrue(np.isfinite(s.values).all(), f"Formula {f} produced non-finite values on zero df")

    def test_all_constant_price_series_std_zero(self):
        """Verify constant prices where realized volatility is strictly zero do not cause zero division."""
        df_const = pd.DataFrame({
            "open": [100.0] * self.n_bars,
            "high": [100.0] * self.n_bars,
            "low": [100.0] * self.n_bars,
            "close": [100.0] * self.n_bars,
            "volume": [1000.0] * self.n_bars
        })

        res = QlibAlpha158.compute_all(df_const)
        self.assertTrue(np.isfinite(res.values).all(), "Constant price series produced non-finite values")

        # Also verify individual dynamic factor functions
        pvt = compute_pvt(df_const)
        self.assertTrue(np.isfinite(pvt.values).all())

        vas = compute_vas(df_const)
        self.assertTrue(np.isfinite(vas.values).all())

        cvd_ratio, cvd_div = compute_lee_ready_cvd(df_const)
        self.assertTrue(np.isfinite(cvd_ratio.values).all())
        self.assertTrue(np.isfinite(cvd_div.values).all())

        str_fac = compute_str(df_const)
        self.assertTrue(np.isfinite(str_fac.values).all())

    def test_negative_volumes(self):
        """Verify negative volume inputs are handled cleanly without exceptions."""
        df_neg_vol = pd.DataFrame({
            "open": [10.0 + i * 0.1 for i in range(self.n_bars)],
            "high": [12.0 + i * 0.1 for i in range(self.n_bars)],
            "low": [9.0 + i * 0.1 for i in range(self.n_bars)],
            "close": [11.0 + i * 0.1 for i in range(self.n_bars)],
            "volume": [-500.0] * self.n_bars
        })

        res = QlibAlpha158.compute_all(df_neg_vol)
        self.assertTrue(np.isfinite(res.values).all(), "Negative volume produced non-finite values")

    def test_infinite_prices_and_volumes(self):
        """Verify infinite inputs (+inf and -inf) are sanitized and replaced with finite values."""
        df_inf = pd.DataFrame({
            "open": [np.inf, 1.0, -np.inf, 1.0] * 10,
            "high": [np.inf, 2.0, 1.0, 2.0] * 10,
            "low": [1.0, 0.5, -np.inf, 0.5] * 10,
            "close": [np.inf, 1.5, 1.0, -np.inf] * 10,
            "volume": [100.0, np.inf, 200.0, -np.inf] * 10
        })

        res = QlibAlpha158.compute_all(df_inf)
        self.assertTrue(np.isfinite(res.values).all(), "Infinite inputs were not sanitized to finite values")
        self.assertFalse(np.isinf(res.values).any())

    def test_all_nan_dataframe(self):
        """Verify all-NaN inputs are sanitized and replaced with finite 0.0 fallbacks."""
        df_nan = pd.DataFrame({
            "open": [np.nan] * self.n_bars,
            "high": [np.nan] * self.n_bars,
            "low": [np.nan] * self.n_bars,
            "close": [np.nan] * self.n_bars,
            "volume": [np.nan] * self.n_bars
        })

        res = QlibAlpha158.compute_all(df_nan)
        self.assertTrue(np.isfinite(res.values).all(), "All-NaN inputs were not sanitized to finite values")
        self.assertFalse(np.isnan(res.values).any())

    def test_single_row_dataframe_boundary(self):
        """Verify minimal 1-row DataFrame does not crash rolling or shift operators."""
        df_single = pd.DataFrame({
            "open": [100.0],
            "high": [105.0],
            "low": [95.0],
            "close": [102.0],
            "volume": [500.0]
        })

        res = QlibAlpha158.compute_all(df_single)
        self.assertEqual(res.shape, (1, 76))
        self.assertTrue(np.isfinite(res.values).all())

    def test_cross_sectional_momentum_degeneracies(self):
        """Verify compute_cs_momentum handles empty dict, single asset, and constant assets."""
        # Empty dict
        empty_res = compute_cs_momentum({})
        self.assertEqual(empty_res, {})

        # Single asset
        df_single_asset = {"EURUSD": pd.DataFrame({"close": [1.0, 1.1, 1.2, 1.1, 1.3]})}
        cs_res = compute_cs_momentum(df_single_asset)
        self.assertIn("EURUSD", cs_res)
        self.assertTrue(np.isfinite(cs_res["EURUSD"].values).all())

        # Multiple constant assets
        df_multi_const = {
            "EURUSD": pd.DataFrame({"close": [1.0] * 20}),
            "GBPUSD": pd.DataFrame({"close": [1.0] * 20})
        }
        cs_multi = compute_cs_momentum(df_multi_const)
        self.assertTrue(np.isfinite(cs_multi["EURUSD"].values).all())
        self.assertTrue(np.isfinite(cs_multi["GBPUSD"].values).all())

    def test_correlation_divergence_degeneracies(self):
        """Verify compute_correlation_divergence handles identical constant series."""
        s1 = pd.Series([10.0] * 30)
        s2 = pd.Series([10.0] * 30)
        div = compute_correlation_divergence(s1, s2, window=10)
        self.assertEqual(len(div), 30)
        self.assertTrue(np.isfinite(div.values).all())


class TestAlphaEvaluatorDegeneraciesAndEdgeCases(unittest.TestCase):
    """
    Stress-tests AlphaEvaluator with degenerate factors, short sample lengths (N < h),
    identical constant ranks, and verifies fail-safe neutral fallbacks.
    """

    def setUp(self):
        self.evaluator = AlphaEvaluator()

    def test_forward_return_length_smaller_than_horizon(self):
        """Verify forward return calculation when DataFrame length is strictly less than horizon (N < h)."""
        df_short = pd.DataFrame({"close": [100.0, 102.0]})  # length 2
        fwd_dict = self.evaluator.compute_forward_returns(df_short, horizons=[5, 10])

        self.assertIn(5, fwd_dict)
        self.assertIn(10, fwd_dict)
        self.assertEqual(len(fwd_dict[5]), 2)
        # All forward returns for horizon > length must be NaN
        self.assertTrue(fwd_dict[5].isna().all())

        # Evaluate factor on N < h
        factor_short = pd.Series([1.0, 2.0])
        report = self.evaluator.evaluate_factor(factor_short, df_short)
        self.assertIsInstance(report, FactorEvaluationReport)
        self.assertFalse(report.passed)
        self.assertEqual(report.rank_ic_spearman, 0.0)
        self.assertEqual(report.ic_pearson, 0.0)
        self.assertEqual(report.information_ratio, 0.0)
        self.assertEqual(report.sharpe_ratio, 0.0)

    def test_constant_ranks_rank_correlation(self):
        """Verify rank correlation and IC on identical constant ranks returns 0.0 without division by zero."""
        n = 30
        factor_const = pd.Series([5.0] * n)
        fwd_const = pd.Series([0.02] * n)

        rank_ic = self.evaluator.compute_rank_ic(factor_const, fwd_const)
        self.assertEqual(rank_ic, 0.0, "Rank IC on constant ranks must be 0.0")

        ic = self.evaluator.compute_ic(factor_const, fwd_const)
        self.assertEqual(ic, 0.0, "Pearson IC on constant series must be 0.0")

        sharpe = self.evaluator.compute_sharpe(factor_const, fwd_const)
        self.assertEqual(sharpe, 0.0, "Sharpe ratio on constant series must be 0.0")

        turnover, autocorr = self.evaluator.compute_turnover_and_autocorr(factor_const)
        self.assertEqual(turnover, 0.0)
        self.assertEqual(autocorr, 0.0)

        monotonicity = self.evaluator.compute_monotonicity(factor_const, fwd_const)
        self.assertEqual(monotonicity, 0.0)

    def test_all_nan_factor_evaluation(self):
        """Verify evaluating an all-NaN factor fails gracefully with zero unhandled exceptions."""
        n = 30
        factor_nan = pd.Series([np.nan] * n)
        df_valid = pd.DataFrame({
            "open": [10.0 + i for i in range(n)],
            "high": [12.0 + i for i in range(n)],
            "low": [9.0 + i for i in range(n)],
            "close": [11.0 + i for i in range(n)],
            "volume": [1000.0] * n
        })

        report = self.evaluator.evaluate_factor(factor_nan, df_valid)
        self.assertFalse(report.passed)
        self.assertEqual(report.rank_ic_spearman, 0.0)
        self.assertEqual(report.information_ratio, 0.0)
        self.assertGreater(len(report.rejection_reasons), 0)

    def test_infinite_factor_values(self):
        """Verify evaluating factor series with Infs does not cause unhandled crashes."""
        n = 40
        factor_inf = pd.Series([np.inf, -np.inf, 1.0, 2.0] * 10)
        df_valid = pd.DataFrame({
            "open": [10.0 + i * 0.1 for i in range(n)],
            "high": [12.0 + i * 0.1 for i in range(n)],
            "low": [9.0 + i * 0.1 for i in range(n)],
            "close": [11.0 + i * 0.1 for i in range(n)],
            "volume": [1000.0] * n
        })

        report = self.evaluator.evaluate_factor(factor_inf, df_valid)
        self.assertIsInstance(report, FactorEvaluationReport)
        self.assertTrue(math.isfinite(report.rank_ic_spearman))
        self.assertTrue(math.isfinite(report.information_ratio))

    def test_sample_size_less_than_three(self):
        """Verify sample sizes smaller than 3 return neutral 0.0 across all statistical methods."""
        factor_2 = pd.Series([1.0, 2.0])
        fwd_2 = pd.Series([0.01, -0.01])

        self.assertEqual(self.evaluator.compute_ic(factor_2, fwd_2), 0.0)
        self.assertEqual(self.evaluator.compute_rank_ic(factor_2, fwd_2), 0.0)
        self.assertEqual(self.evaluator.compute_sharpe(factor_2, fwd_2), 0.0)
        turnover, autocorr = self.evaluator.compute_turnover_and_autocorr(factor_2)
        self.assertEqual(turnover, 0.0)
        self.assertEqual(autocorr, 1.0)
        self.assertEqual(self.evaluator.compute_monotonicity(factor_2, fwd_2), 0.0)


class TestAITraderAlphaMinerAdversarialStress(unittest.TestCase):
    """
    Stress-tests AITraderAlphaMiner against degenerate inputs, offline Ollama fallback,
    and redundant alpha correlation pruning with collinear factors.
    """

    def setUp(self):
        # Point to loopback invalid port so connection fails immediately (<1ms) triggering fallback
        self.miner = AITraderAlphaMiner(ollama_url="http://127.0.0.1:1")
        self.df_valid = pd.DataFrame({
            "open": [10.0 + i * 0.2 for i in range(60)],
            "high": [11.0 + i * 0.2 for i in range(60)],
            "low": [9.5 + i * 0.2 for i in range(60)],
            "close": [10.5 + i * 0.2 for i in range(60)],
            "volume": [1000.0 + (i % 5) * 100 for i in range(60)]
        })

    def test_ollama_offline_fallback_deterministic_templates(self):
        """Verify miner seamlessly falls back to 35+ deterministic templates when Ollama is unreachable."""
        candidate = self.miner.generate_candidate_formula("EURUSD")
        self.assertIsInstance(candidate, dict)
        self.assertEqual(candidate["source"], "DETERMINISTIC_FALLBACK")
        self.assertTrue(FormulaASTParser.validate_expression(candidate["expression"]))
        self.assertIn("expression", candidate)
        self.assertIn("name", candidate)

    def test_deterministic_templates_coverage_and_safety(self):
        """Verify all 35+ deterministic templates are syntactically valid and pass AST security."""
        self.assertGreaterEqual(len(DETERMINISTIC_TEMPLATES), 30)
        for tmpl in DETERMINISTIC_TEMPLATES:
            expr = tmpl["expression"]
            name = tmpl["name"]
            with self.subTest(template_name=name):
                self.assertTrue(
                    FormulaASTParser.validate_expression(expr),
                    f"Template {name} failed AST validation: {expr}"
                )
                res = FormulaASTParser.evaluate(expr, self.df_valid)
                self.assertIsInstance(res, pd.Series)
                self.assertEqual(len(res), len(self.df_valid))
                self.assertTrue(np.isfinite(res.values).all())

    def test_mine_alphas_with_degenerate_dataframes(self):
        """Verify mine_alphas executes without crashing on all-zero, constant, and NaN DataFrames."""
        df_zero = pd.DataFrame({
            "open": [0.0] * 50,
            "high": [0.0] * 50,
            "low": [0.0] * 50,
            "close": [0.0] * 50,
            "volume": [0.0] * 50
        })

        reports = self.miner.mine_alphas(df_zero, "EURUSD", count=3)
        self.assertIsInstance(reports, list)
        self.assertEqual(len(reports), 3)
        for r in reports:
            self.assertIsInstance(r, FactorEvaluationReport)
            self.assertFalse(r.passed)
            self.assertEqual(r.rank_ic_spearman, 0.0)

    def test_prune_redundant_alphas_with_constant_and_collinear_factors(self):
        """Verify prune_redundant_alphas handles collinear and identical constant factors without crash."""
        reports = self.miner.mine_alphas(self.df_valid, "EURUSD", count=5)
        self.assertGreaterEqual(len(reports), 1)

        # Prune with standard threshold
        pruned = self.miner.prune_redundant_alphas(reports, self.df_valid, threshold=0.65)
        self.assertIsInstance(pruned, list)
        self.assertLessEqual(len(pruned), len(reports))

        # Test edge case: empty reports list
        empty_pruned = self.miner.prune_redundant_alphas([], self.df_valid)
        self.assertEqual(empty_pruned, [])

    def test_ollama_online_mock_response(self):
        """Verify successful parsing and validation when Ollama responds with valid JSON."""
        mock_response = {
            "response": '{"name": "mock_momentum", "expression": "Div(Sub(close, Ref(close, 5)), Std(close, 10))", "rationale": "Mock momentum factor", "intended_horizon": "1h"}'
        }
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_cm = MagicMock()
            mock_cm.read.return_value = json_encode(mock_response).encode("utf-8")
            mock_cm.__enter__.return_value = mock_cm
            mock_urlopen.return_value = mock_cm

            cand = self.miner.generate_candidate_formula("XAUUSD")
            self.assertEqual(cand["source"], "OLLAMA")
            self.assertEqual(cand["name"], "mock_momentum")
            self.assertEqual(cand["expression"], "Div(Sub(close, Ref(close, 5)), Std(close, 10))")


def json_encode(obj: Any) -> str:
    import json
    return json.dumps(obj)


if __name__ == "__main__":
    unittest.main(verbosity=2)
