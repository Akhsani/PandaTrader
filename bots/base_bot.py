"""
Base utilities for 3Commas bot simulators.
Provides OHLCV loading, fee engine, equity tracking, and performance metrics.
"""
import os
from typing import Optional
import pandas as pd
import numpy as np

# Add project root for imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.data_loader import load_ohlcv
from utils.backtest_utils import get_performance_metrics


def load_ohlcv_for_bot(path: str, date_col: str = None) -> pd.DataFrame:
    """
    Load OHLCV and ensure lowercase columns: open, high, low, close, volume.
    Returns DataFrame with DatetimeIndex.
    """
    df = load_ohlcv(path, date_col)
    df.columns = [c.lower() for c in df.columns]
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV missing columns: {missing}. Got: {list(df.columns)}")
    return df


class FeeEngine:
    """
    Configurable fee and slippage for buy and sell fills.
    Default 0.001 (0.1%) per side for Binance Spot.
    slippage_bps: basis points (1 bps = 0.01%); e.g. 10 = 0.1% slippage.
    """

    def __init__(self, fee: float = 0.001, slippage_bps: float = 0.0):
        self.fee = fee
        self.slippage = slippage_bps / 10000.0 if slippage_bps else 0.0

    def apply_buy_fee(self, usdt_amount: float) -> float:
        """Cost in USDT to buy (fee + slippage reduce effective quantity)."""
        return usdt_amount * (1 + self.fee + self.slippage)

    def apply_sell_fee(self, usdt_amount: float) -> float:
        """Proceeds after sell fee and slippage."""
        return usdt_amount * (1 - self.fee - self.slippage)

    def cost_for_quantity(self, quantity: float, price: float, side: str = "buy") -> float:
        """Total cost (including fee and slippage) for a fill."""
        notional = quantity * price
        if side == "buy":
            return notional * (1 + self.fee + self.slippage)
        return notional * (1 - self.fee - self.slippage)


def compute_bot_metrics(
    closed_deals: list,
    equity_curve: list,
    initial_capital: float,
    annual_factor: int = 365 * 24,
) -> dict:
    """
    Compute performance metrics for bot simulation.
    closed_deals: list of dicts with 'pnl', 'entry_time', 'exit_time', etc.
    equity_curve: list of equity values over time.
    annual_factor: for Sharpe (e.g. 365*24 for hourly data).
    """
    metrics = {
        "total_deals": len(closed_deals),
        "win_rate": 0.0,
        "avg_deal_duration_hours": 0.0,
        "total_return_pct": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown_pct": 0.0,
        "max_capital_deployed": initial_capital,
    }

    if not closed_deals:
        return metrics

    pnls = [d.get("pnl", 0) for d in closed_deals if "pnl" in d]
    if not pnls:
        return metrics

    wins = sum(1 for p in pnls if p > 0)
    metrics["win_rate"] = wins / len(pnls)

    # Deal duration (hours)
    durations = []
    for d in closed_deals:
        et = d.get("entry_time")
        xt = d.get("exit_time")
        if et is not None and xt is not None:
            if hasattr(et, "to_pydatetime"):
                et = et.to_pydatetime()
            if hasattr(xt, "to_pydatetime"):
                xt = xt.to_pydatetime()
            delta = (xt - et).total_seconds() / 3600
            durations.append(delta)
    metrics["avg_deal_duration_hours"] = np.mean(durations) if durations else 0

    # Returns-based metrics
    returns = pd.Series(pnls)
    total_return = (1 + returns).prod() - 1
    metrics["total_return_pct"] = total_return * 100

    # Sharpe from trade returns (approximation when no equity curve)
    std = returns.std()
    if std and std > 0:
        n = len(returns)
        metrics["sharpe_ratio"] = float(returns.mean() / std * np.sqrt(annual_factor / max(n, 1)))

    # Drawdown and Sharpe from equity curve when available
    if equity_curve and len(equity_curve) > 1:
        eq = np.array(equity_curve, dtype=float)
        peak = np.maximum.accumulate(eq)
        dd = (eq - peak) / np.where(peak > 0, peak, 1)
        metrics["max_drawdown_pct"] = float(np.min(dd) * 100)
        metrics["max_capital_deployed"] = float(np.max(eq))
        # Period returns from equity for Sharpe
        eq_series = pd.Series(eq)
        period_returns = eq_series.pct_change().dropna()
        if len(period_returns) > 1 and period_returns.std() > 0:
            pm = get_performance_metrics(period_returns, annual_factor=annual_factor)
            metrics["sharpe_ratio"] = pm.get("sharpe", metrics["sharpe_ratio"])

    return metrics
