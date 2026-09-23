import json
import logging
import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from src.market_analyzer import MarketAnalyzer
from src.strategy import StrategyEngine
from src.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class Backtester:
    """
    Historical Backtesting Engine for Strategy Validation.
    Evaluates historical win rate, drawdown, and profit metrics.
    """

    def __init__(self, config_path: str = "config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)

        self.initial_balance = self.config["account_info"]["target_account_size"]
        self.risk_manager = RiskManager(self.config)
        self.analyzer = MarketAnalyzer(self.config)
        self.strategy = StrategyEngine(self.config)

    @staticmethod
    def _validate_market_frame(df: pd.DataFrame, name: str) -> pd.DataFrame:
        required = {"time", "open", "high", "low", "close"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"{name} is missing columns: {sorted(missing)}")
        clean = df.copy()
        clean["time"] = pd.to_datetime(clean["time"], utc=True)
        clean = clean.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
        numeric = clean[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy()).all():
            raise ValueError(f"{name} contains NaN or infinite OHLC values")
        if ((numeric["high"] < numeric[["open", "close", "low"]].max(axis=1)) |
                (numeric["low"] > numeric[["open", "close", "high"]].min(axis=1))).any():
            raise ValueError(f"{name} contains invalid OHLC geometry")
        clean[["open", "high", "low", "close"]] = numeric
        return clean

    @staticmethod
    def _estimated_round_trip_cost(
        symbol: str,
        lots: float,
        entry_price: float,
        contract_size: float,
        commission_per_lot: float = 7.0,
    ) -> float:
        """Conservative deterministic spread + two-sided slippage + commission model."""
        sym_u = symbol.upper()
        if "XAU" in sym_u or "GOLD" in sym_u:
            spread_price, slippage_price = 0.30, 0.10
        elif any(token in sym_u for token in ("BTC", "ETH", "SOL", "WIF", "PEPE", "BONK")):
            spread_price, slippage_price = entry_price * 0.0004, entry_price * 0.0002
            commission_per_lot = 0.5
        elif "JPY" in sym_u:
            spread_price, slippage_price = 0.015, 0.005
        else:
            spread_price, slippage_price = 0.00015, 0.00005
        market_impact = lots * contract_size * (spread_price + 2.0 * slippage_price)
        return max(0.0, market_impact + lots * commission_per_lot)

    def run_backtest(
        self,
        symbol: str,
        df_h1: pd.DataFrame,
        df_m15: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        step: int = 2
    ) -> Dict[str, Any]:
        """
        Executes backtest over historical DataFrames with full Smart Money SMC reasoning.
        """
        df_h1 = self._validate_market_frame(df_h1, "df_h1")
        df_m15 = self._validate_market_frame(df_m15, "df_m15")
        balance = self.initial_balance
        equity_curve = [balance]
        trades: List[Dict[str, Any]] = []

        window_size = 100
        horizon = 40
        next_entry_index = window_size
        total_costs = 0.0

        ts_start = pd.to_datetime(start_date, utc=True) if start_date else None
        ts_end = pd.to_datetime(end_date, utc=True) if end_date else None

        sym_u = symbol.upper()
        if "XAU" in sym_u or "GOLD" in sym_u:
            contract_size = 100
            point = 0.01
        elif any(c in sym_u for c in ["BTC", "ETH", "SOL", "WIF"]):
            contract_size = 1
            point = 0.01 if "WIF" not in sym_u else 0.0001
        elif "PEPE" in sym_u or "BONK" in sym_u:
            contract_size = 1000000
            point = 0.00000001
        else:  # Forex
            contract_size = 100000
            point = 0.01 if "JPY" in sym_u else 0.00001

        symbol_info = {
            "trade_contract_size": contract_size,
            "point": point,
            "volume_min": 0.01,
            "volume_step": 0.01,
            "volume_max": 20.0
        }

        for i in range(window_size, len(df_m15) - horizon, step):
            if i < next_entry_index:
                continue
            sub_m15 = df_m15.iloc[i-window_size:i].copy().reset_index(drop=True)
            sub_h1 = df_h1[df_h1['time'] <= sub_m15['time'].iloc[-1]].copy().reset_index(drop=True)

            candle_ts = sub_m15['time'].iloc[-1]
            if ts_start and candle_ts < ts_start:
                continue
            if ts_end and candle_ts > ts_end:
                break

            if len(sub_h1) < 20 or len(sub_m15) < 20:
                continue

            analysis = self.analyzer.analyze_symbol(symbol, sub_h1, sub_m15)
            signal = self.strategy.evaluate_signals(analysis)

            if signal:
                entry_price = signal["entry_price"]
                sl_price = signal["sl_price"]
                tp_price = signal["tp_price"]

                # Risk Sizing
                lot_size, risk_dollars = self.risk_manager.calculate_position_size(
                    symbol, entry_price, sl_price, balance, symbol_info
                )

                # Future candles simulation
                future_m15 = df_m15.iloc[i:i+horizon]
                outcome = "EXPIRED"
                exit_offset = horizon - 1
                exit_price = float(future_m15.iloc[exit_offset]["close"])
                r_multiple = 0.0
                gross_pnl = 0.0

                for offset, (_, bar) in enumerate(future_m15.iterrows()):
                    high = bar['high']
                    low = bar['low']

                    if signal["signal"] == "BUY":
                        stop_hit = low <= sl_price
                        target_hit = high >= tp_price
                        if stop_hit:  # Conservative if both are touched in one bar.
                            outcome = "LOSS"
                            exit_price = sl_price
                            r_multiple = -1.0
                            gross_pnl = -risk_dollars
                            exit_offset = offset
                            break
                        elif target_hit:
                            outcome = "WIN"
                            exit_price = tp_price
                            r_multiple = abs(tp_price - entry_price) / max(abs(entry_price - sl_price), 1e-12)
                            gross_pnl = risk_dollars * r_multiple
                            exit_offset = offset
                            break
                    elif signal["signal"] == "SELL":
                        stop_hit = high >= sl_price
                        target_hit = low <= tp_price
                        if stop_hit:
                            outcome = "LOSS"
                            exit_price = sl_price
                            r_multiple = -1.0
                            gross_pnl = -risk_dollars
                            exit_offset = offset
                            break
                        elif target_hit:
                            outcome = "WIN"
                            exit_price = tp_price
                            r_multiple = abs(entry_price - tp_price) / max(abs(sl_price - entry_price), 1e-12)
                            gross_pnl = risk_dollars * r_multiple
                            exit_offset = offset
                            break

                if outcome == "EXPIRED":
                    exit_price = float(future_m15.iloc[exit_offset]["close"])
                    if signal["signal"] == "BUY":
                        r_multiple = (exit_price - entry_price) / max(abs(entry_price - sl_price), 1e-12)
                    else:
                        r_multiple = (entry_price - exit_price) / max(abs(sl_price - entry_price), 1e-12)
                    gross_pnl = risk_dollars * r_multiple

                estimated_cost = self._estimated_round_trip_cost(symbol, lot_size, entry_price, contract_size)
                net_pnl = gross_pnl - estimated_cost
                if outcome == "EXPIRED":
                    outcome = "WIN" if net_pnl > 0 else ("LOSS" if net_pnl < 0 else "EXPIRED")
                total_costs += estimated_cost
                balance += net_pnl
                equity_curve.append(balance)
                next_entry_index = i + exit_offset + 1

                dec = 8 if ("PEPE" in sym_u or "BONK" in sym_u) else (4 if "WIF" in sym_u else (2 if any(m in sym_u for m in ["XAU", "BTC", "ETH", "SOL"]) else 5))

                trades.append({
                    "symbol": symbol,
                    "type": signal["signal"],
                    "direction": signal["signal"],
                    "entry_time": str(sub_m15['time'].iloc[-1]),
                    "entry_price": round(float(entry_price), dec),
                    "exit_time": str(future_m15.iloc[exit_offset]["time"]),
                    "exit_price": round(float(exit_price), dec),
                    "sl_price": round(float(sl_price), dec),
                    "tp_price": round(float(tp_price), dec),
                    "lot_size": round(float(lot_size), 4),
                    "risk_dollars": round(float(risk_dollars), 2),
                    "outcome": outcome,
                    "r_multiple": round(float(r_multiple), 2),
                    "gross_pnl": round(float(gross_pnl), 2),
                    "estimated_cost": round(float(estimated_cost), 2),
                    "pnl": round(float(net_pnl), 2),
                    "net_pnl": round(float(net_pnl), 2),
                    "balance": round(float(balance), 2),
                    "pattern": signal.get("pattern", "PRICE_ACTION"),
                    "setup_reasoning": signal.get("reason", "Smart Money Setup"),
                    "session": signal.get("session", "OFF_HOURS"),
                    "confluence_score": round(float(signal.get("confluence_score", 1.0)), 2)
                })

        # Calculate Statistics
        total_trades = len(trades)
        wins = len([t for t in trades if t["outcome"] == "WIN"])
        losses = len([t for t in trades if t["outcome"] == "LOSS"])
        expired = len([t for t in trades if t["outcome"] == "EXPIRED"])
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
        total_pnl = balance - self.initial_balance

        # Calculate Max Drawdown %
        equity_series = pd.Series(equity_curve)
        cummax = equity_series.cummax()
        drawdowns = (cummax - equity_series) / cummax * 100
        max_drawdown_pct = float(drawdowns.max()) if not drawdowns.empty else 0.0
        pnl_values = np.array([float(t["pnl"]) for t in trades], dtype=float)
        pnl_std = float(pnl_values.std(ddof=1)) if len(pnl_values) > 1 else 0.0
        trade_sharpe = float(pnl_values.mean() / pnl_std * math.sqrt(len(pnl_values))) if pnl_std > 0 else 0.0
        gross_wins = sum(max(0.0, float(t["pnl"])) for t in trades)
        gross_losses = abs(sum(min(0.0, float(t["pnl"])) for t in trades))
        profit_factor = gross_wins / gross_losses if gross_losses > 0 else (float("inf") if gross_wins > 0 else 0.0)
        readiness_reasons = []
        if total_trades < 50:
            readiness_reasons.append("Fewer than 50 non-overlapping trades")
        if total_pnl <= 0:
            readiness_reasons.append("Net PnL is not positive after estimated costs")
        if max_drawdown_pct > 10.0:
            readiness_reasons.append("Maximum drawdown exceeds 10% research ceiling")

        report = {
            "symbol": symbol,
            "initial_balance": self.initial_balance,
            "final_balance": round(balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round((total_pnl / self.initial_balance) * 100, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "expired": expired,
            "win_rate_pct": round(win_rate, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "estimated_total_costs": round(total_costs, 2),
            "trade_sharpe": round(trade_sharpe, 3),
            "profit_factor": round(profit_factor, 3) if math.isfinite(profit_factor) else "Infinity",
            "overlapping_positions_allowed": False,
            "same_bar_sl_tp_policy": "STOP_FIRST_CONSERVATIVE",
            "research_ready": not readiness_reasons,
            "readiness_reasons": readiness_reasons,
            "trades": trades
        }
        return report

    def run_walk_forward(
        self,
        symbol: str,
        df_h1: pd.DataFrame,
        df_m15: pd.DataFrame,
        folds: int = 4,
    ) -> Dict[str, Any]:
        """Run chronological, non-shuffled evaluation folds and expose each result."""
        if folds < 2:
            raise ValueError("folds must be at least 2")
        h1 = self._validate_market_frame(df_h1, "df_h1")
        m15 = self._validate_market_frame(df_m15, "df_m15")
        boundaries = np.linspace(0, len(m15), folds + 1, dtype=int)
        fold_reports = []
        for fold in range(folds):
            start, end = int(boundaries[fold]), int(boundaries[fold + 1])
            segment = m15.iloc[start:end].copy()
            if len(segment) < 160:
                continue
            h1_segment = h1[h1["time"] <= segment["time"].iloc[-1]].copy()
            report = self.run_backtest(symbol, h1_segment, segment)
            fold_reports.append({
                "fold": fold + 1,
                "start": segment["time"].iloc[0].isoformat(),
                "end": segment["time"].iloc[-1].isoformat(),
                "report": report,
            })
        profitable = sum(1 for item in fold_reports if item["report"]["total_pnl"] > 0)
        return {
            "symbol": symbol,
            "folds_requested": folds,
            "folds_evaluated": len(fold_reports),
            "profitable_folds": profitable,
            "all_folds_profitable": bool(fold_reports) and profitable == len(fold_reports),
            "reports": fold_reports,
        }

if __name__ == "__main__":
    from src.mt5_connector import MT5Connector
    mt5_conn = MT5Connector(simulation_mode=True)
    h1_df = mt5_conn.get_rates("EURUSD", "H1", num_candles=500)
    m15_df = mt5_conn.get_rates("EURUSD", "M15", num_candles=1000)

    bt = Backtester()
    res = bt.run_backtest("EURUSD", h1_df, m15_df)
    print(json.dumps({k: v for k, v in res.items() if k != 'trades'}, indent=2))
