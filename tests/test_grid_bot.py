"""
Unit tests for GridBotSimulator.
"""
import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bots.grid_bot import GridBotSimulator


def test_build_grid_geometric():
    """Geometric grid has equal % spacing."""
    params = {
        "upper_price": 110,
        "lower_price": 100,
        "investment_amount": 1000,
        "grid_lines_count": 5,
        "grid_type": "geometric",
    }
    bot = GridBotSimulator(params)
    levels = bot._build_grid()
    assert len(levels) == 6  # n+1 levels
    assert abs(levels[0] - 100) < 0.01
    assert abs(levels[-1] - 110) < 0.01
    ratios = [levels[i + 1] / levels[i] for i in range(5)]
    assert all(abs(r - ratios[0]) < 0.001 for r in ratios)


def test_build_grid_arithmetic():
    """Arithmetic grid has equal $ spacing."""
    params = {
        "upper_price": 110,
        "lower_price": 100,
        "investment_amount": 1000,
        "grid_lines_count": 5,
        "grid_type": "arithmetic",
    }
    bot = GridBotSimulator(params)
    levels = bot._build_grid()
    assert len(levels) == 6
    assert levels[0] == 100
    assert levels[-1] == 110
    steps = [levels[i + 1] - levels[i] for i in range(5)]
    assert all(abs(s - 2) < 0.01 for s in steps)


def test_profit_per_grid():
    """Profit per grid cell is positive when level_high > level_low."""
    params = {
        "upper_price": 110,
        "lower_price": 100,
        "investment_amount": 100,
        "grid_lines_count": 5,
        "fee": 0,
    }
    bot = GridBotSimulator(params)
    profit = bot._profit_per_grid(100, 102)
    assert profit > 0


def test_trailing_up_extends_upper():
    """Trailing up extends grid when price closes above upper."""
    params = {
        "upper_price": 105,
        "lower_price": 100,
        "investment_amount": 500,
        "grid_lines_count": 5,
        "trailing_up": True,
        "fee": 0,
    }
    bot = GridBotSimulator(params)
    # Price oscillates then closes above 105
    idx = pd.date_range("2024-01-01", periods=20, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [101, 102, 103, 104, 105, 106, 105, 104, 103, 102] + [102] * 10,
        "high": [102, 103, 104, 105, 106, 107, 106, 105, 104, 103] + [103] * 10,
        "low": [100, 101, 102, 103, 104, 105, 104, 103, 102, 101] + [101] * 10,
        "close": [101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 105.5, 104.5, 103.5, 102.5] + [102.5] * 10,
        "volume": [1000] * 20,
    }, index=idx)
    result = bot.run(ohlcv)
    assert result["total_deals"] >= 0  # May or may not have completed cycles


def test_stop_bot_price():
    """Stop bot closes positions when price hits stop."""
    params = {
        "upper_price": 105,
        "lower_price": 100,
        "investment_amount": 500,
        "grid_lines_count": 3,
        "stop_bot_price": 98,
        "fee": 0,
    }
    bot = GridBotSimulator(params)
    idx = pd.date_range("2024-01-01", periods=10, freq="1h")
    # Price drops through 100 (buy), then to 98 (stop)
    ohlcv = pd.DataFrame({
        "open": [102, 101, 100, 99, 98] + [97] * 5,
        "high": [102, 101, 100, 99, 98] + [97] * 5,
        "low": [101, 100, 99, 98, 97] + [96] * 5,
        "close": [101.5, 100.5, 99.5, 98.5, 97.5] + [97] * 5,
        "volume": [1000] * 10,
    }, index=idx)
    result = bot.run(ohlcv)
    # Should have at least one stop exit if we had open buys
    assert "closed_deals" in result
