"""
Unit tests for WalkForwardAnalyzer.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer


def _make_price_df(days=400):
    """Generate synthetic OHLCV for testing."""
    idx = pd.date_range(start="2024-01-01", periods=days * 24, freq="h")
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(len(idx)) * 0.5)
    df = pd.DataFrame({
        "open": close,
        "high": close + np.abs(np.random.randn(len(idx))),
        "low": close - np.abs(np.random.randn(len(idx))),
        "close": close,
        "volume": np.ones(len(idx)) * 1000,
    }, index=idx)
    df.index.name = "datetime"
    return df


def _dca_strategy(price_df, funding_df=None, **params):
    """Dummy DCA: returns compounding pnl."""
    if price_df is None or len(price_df) < 50:
        return pd.DataFrame()
    n = min(20, len(price_df) // 10)
    step = max(1, len(price_df) // n)
    idx = price_df.index[step:step * n:step][:n]
    if len(idx) == 0:
        return pd.DataFrame()
    pnl = [0.02] * len(idx)
    return pd.DataFrame({
        "pnl": pnl,
        "exit_time": idx,
        "entry_time": idx - timedelta(hours=1),
        "exit_reason": ["tp"] * len(idx),
    })


def _grid_strategy(price_df, funding_df=None, **params):
    """Dummy grid: returns many small per-cell pnl (sum scoring)."""
    if price_df is None or len(price_df) < 50:
        return pd.DataFrame()
    n = min(100, len(price_df) // 5)
    step = max(1, len(price_df) // n)
    idx = price_df.index[step:step * n:step][:n]
    if len(idx) == 0:
        return pd.DataFrame()
    pnl = [0.001] * len(idx)
    return pd.DataFrame({
        "pnl": pnl,
        "exit_time": idx,
        "entry_time": idx - timedelta(hours=1),
        "exit_reason": ["grid"] * len(idx),
    })


def test_walk_forward_compound_scoring():
    """Compound mode uses (1+pnl).prod()-1 for scoring."""
    price_df = _make_price_df(400)
    param_grid = {"x": [1]}
    analyzer = WalkForwardAnalyzer(
        _dca_strategy, param_grid, price_df,
        train_window_days=60, test_window_days=30,
        score_mode="compound",
    )
    results = analyzer.run()
    assert not results.empty
    total_return = (results["pnl"] + 1).prod() - 1
    assert total_return > 0


def test_walk_forward_sum_scoring():
    """Sum mode uses pnl.sum() for grid strategies."""
    price_df = _make_price_df(400)
    param_grid = {"x": [1]}
    analyzer = WalkForwardAnalyzer(
        _grid_strategy, param_grid, price_df,
        train_window_days=60, test_window_days=30,
        score_mode="sum",
    )
    results = analyzer.run()
    assert not results.empty
    total_return = results["pnl"].sum()
    assert total_return > 0
    # Sum should be much smaller than compound for many small returns
    compound_return = (results["pnl"] + 1).prod() - 1
    assert total_return < compound_return
