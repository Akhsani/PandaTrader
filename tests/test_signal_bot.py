"""
Unit tests for SignalBotSimulator.
"""
import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bots.signal_bot import SignalBotSimulator


def test_entry_on_signal():
    """Entry occurs when signal is True."""
    params = {
        "position_size": 100,
        "take_profit_percentage": 5.0,
        "stop_loss_percentage": 3.0,
        "fee": 0,
    }
    bot = SignalBotSimulator(params)
    idx = pd.date_range("2024-01-01", periods=10, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [100] * 10,
        "high": [106] * 10,
        "low": [99] * 10,
        "close": [105] * 10,
        "volume": [1000] * 10,
    }, index=idx)
    signal = pd.Series([False, True] + [False] * 8, index=idx)
    result = bot.run(ohlcv, signal)
    assert result["total_deals"] == 1
    assert result["closed_deals"][0]["exit_reason"] == "take_profit"


def test_stop_loss_exit():
    """SL triggers when low <= sl_price."""
    params = {
        "position_size": 100,
        "take_profit_percentage": 10.0,
        "stop_loss_percentage": 2.0,
        "fee": 0,
    }
    bot = SignalBotSimulator(params)
    idx = pd.date_range("2024-01-01", periods=10, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [100, 100, 97, 96] + [95] * 6,
        "high": [101, 100, 98, 97] + [96] * 6,
        "low": [99, 98, 97, 96] + [95] * 6,
        "close": [100, 98, 97, 96] + [95] * 6,
        "volume": [1000] * 10,
    }, index=idx)
    signal = pd.Series([False, True] + [False] * 8, index=idx)
    result = bot.run(ohlcv, signal)
    assert result["total_deals"] == 1
    assert result["closed_deals"][0]["exit_reason"] == "stop_loss"


def test_trailing_stop():
    """Trailing stop closes on reversal from high."""
    params = {
        "position_size": 100,
        "take_profit_percentage": 10.0,
        "stop_loss_percentage": 5.0,
        "trailing_stop_loss": True,
        "trailing_stop_loss_percentage": 2.0,
        "fee": 0,
    }
    bot = SignalBotSimulator(params)
    idx = pd.date_range("2024-01-01", periods=10, freq="1h")
    # Entry 100. High goes to 108. Trailing: 108 * 0.98 = 105.84. Low drops to 105 -> close
    ohlcv = pd.DataFrame({
        "open": [100, 100, 102, 104, 106, 107, 106, 105, 104, 103],
        "high": [101, 102, 104, 106, 108, 108, 107, 106, 105, 104],
        "low": [99, 100, 101, 103, 105, 106, 105, 104, 103, 102],
        "close": [100, 101, 103, 105, 107, 107, 106, 105, 104, 103],
        "volume": [1000] * 10,
    }, index=idx)
    signal = pd.Series([False, True] + [False] * 8, index=idx)
    result = bot.run(ohlcv, signal)
    assert result["total_deals"] == 1
    assert result["closed_deals"][0]["exit_reason"] in ("trailing_stop", "take_profit")
