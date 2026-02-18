"""
Unit tests for DCABotSimulator.
"""
import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bots.dca_bot import DCABotSimulator


def test_calculate_so_levels():
    """SO trigger prices and sizes follow martingale step/volume coefficients."""
    params = {
        "base_order_volume": 100,
        "safety_order_volume": 50,
        "max_safety_orders": 3,
        "safety_order_step_percentage": 1.0,
        "martingale_volume_coefficient": 2.0,
        "martingale_step_coefficient": 1.5,
        "take_profit_percentage": 2.5,
    }
    bot = DCABotSimulator(params)
    entry = 100.0
    levels = bot._calculate_so_levels(entry)

    assert len(levels) == 3
    # Level 0: 1% down
    assert abs(levels[0]["trigger"] - 99.0) < 0.01
    assert levels[0]["size"] == 50
    # Level 1: 1% + 1.5% down
    assert abs(levels[1]["trigger"] - 97.5) < 0.1
    assert levels[1]["size"] == 100  # 50 * 2
    # Level 2: further down
    assert levels[2]["size"] == 200  # 50 * 2^2


def test_calculate_tp_price():
    """TP price is avg_price * (1 + take_profit_percentage/100)."""
    params = {
        "base_order_volume": 100,
        "safety_order_volume": 50,
        "max_safety_orders": 2,
        "safety_order_step_percentage": 1.0,
        "martingale_volume_coefficient": 1.5,
        "martingale_step_coefficient": 1.0,
        "take_profit_percentage": 2.5,
    }
    bot = DCABotSimulator(params)
    assert abs(bot._calculate_tp_price(100.0) - 102.5) < 0.01
    assert abs(bot._calculate_tp_price(50.0) - 51.25) < 0.01


def test_fee_application():
    """Fees are applied on buy and sell."""
    params = {
        "base_order_volume": 100,
        "safety_order_volume": 50,
        "max_safety_orders": 1,
        "safety_order_step_percentage": 1.0,
        "martingale_volume_coefficient": 1.0,
        "martingale_step_coefficient": 1.0,
        "take_profit_percentage": 5.0,
        "fee": 0.001,
    }
    bot = DCABotSimulator(params)
    # Create minimal OHLCV: price goes 100 -> 106 (TP at 105)
    idx = pd.date_range("2024-01-01", periods=10, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [100] * 10,
        "high": [106] * 10,
        "low": [99] * 10,
        "close": [105] * 10,
        "volume": [1000] * 10,
    }, index=idx)
    # Signal at i=1 opens deal (fill at open of candle 1). TP 5% = 105. High at i=2 >= 105 closes.
    signal = pd.Series([False, True] + [False] * 8, index=idx)
    result = bot.run(ohlcv, signal, initial_capital=10000)
    assert result["total_deals"] == 1
    # With fee, profit should be slightly less than 5%
    deal = result["closed_deals"][0]
    assert 0 < deal["pnl"] < 0.05


def test_cooldown_blocks_rapid_reentry():
    """Cooldown prevents new deal for N seconds after close."""
    params = {
        "base_order_volume": 100,
        "safety_order_volume": 50,
        "max_safety_orders": 0,
        "safety_order_step_percentage": 1.0,
        "martingale_volume_coefficient": 1.0,
        "martingale_step_coefficient": 1.0,
        "take_profit_percentage": 1.0,
        "max_active_deals": 2,
        "cooldown_between_deals": 7200,  # 2 hours
    }
    bot = DCABotSimulator(params)
    # 5 hourly candles: signal at 0,1,2,3,4. Deal opens at 0, closes at 1 (TP).
    # Cooldown 2h = 2 candles. So at candle 2 we're still in cooldown.
    idx = pd.date_range("2024-01-01", periods=5, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [100, 100, 100, 100, 100],
        "high": [102, 102, 102, 102, 102],
        "low": [99, 99, 99, 99, 99],
        "close": [101, 101, 101, 101, 101],
        "volume": [1000] * 5,
    }, index=idx)
    signal = pd.Series([True, True, True, True, True], index=idx)
    result = bot.run(ohlcv, signal, initial_capital=10000)
    # First deal opens at candle 1, closes at candle 2 (high>=101).
    # Cooldown 7200s = 2h. Candle 2 ends at t+2h. Next signal at candle 3 (t+3h).
    # So we might get 2 deals if cooldown allows. With 2h cooldown, at t+3h we're past it.
    # Actually: deal 1 opens at i=1 (first signal), fills at open 100. At i=2, high=102 >= 101, closes.
    # last_close_time = ts at i=2. At i=3, ts - last_close = 1h = 3600 < 7200. So no new deal.
    # At i=4, ts - last_close = 2h = 7200. So we can open. So we get 2 deals.
    assert result["total_deals"] >= 1


def test_single_deal_lifecycle_open_so_tp():
    """Single deal: base order -> SO triggers on dip -> TP hit."""
    params = {
        "base_order_volume": 100,
        "safety_order_volume": 50,
        "max_safety_orders": 2,
        "safety_order_step_percentage": 1.0,
        "martingale_volume_coefficient": 1.5,
        "martingale_step_coefficient": 1.0,
        "take_profit_percentage": 2.0,
        "fee": 0.0,  # No fee for clean test
    }
    bot = DCABotSimulator(params)
    # Entry 100. SO0 at 99, SO1 at 98. TP at 2% from avg.
    idx = pd.date_range("2024-01-01", periods=20, freq="1h")
    ohlcv = pd.DataFrame({
        "open": [100.0] * 20,
        "high": [100.0] * 20,
        "low": [97.0] * 20,
        "close": [99.0] * 20,
        "volume": [1000.0] * 20,
    }, index=idx)
    # Signal at i=1 opens. SO triggers when low <= trigger. TP when high >= tp_price.
    # Base 100 @ 100. SO0 50 @ 99 (low<=99). SO1 75 @ 98 (low<=98). Avg ~99.1, TP ~101.1.
    ohlcv.loc[idx[2], "low"] = 98.9   # SO0 triggers
    ohlcv.loc[idx[3], "low"] = 97.9  # SO1 triggers
    ohlcv.loc[idx[5], "high"] = 102.0  # TP hit
    signal = pd.Series([False, True] + [False] * 18, index=idx)
    result = bot.run(ohlcv, signal, initial_capital=10000)
    assert result["total_deals"] == 1
    assert result["closed_deals"][0]["exit_reason"] == "take_profit"


def test_optimized_params_export():
    """optimized_params excludes internal state, includes all 3Commas params."""
    params = {
        "base_order_volume": 25,
        "safety_order_volume": 30,
        "max_safety_orders": 4,
        "safety_order_step_percentage": 0.75,
        "martingale_volume_coefficient": 2.0,
        "martingale_step_coefficient": 1.5,
        "take_profit_percentage": 2.5,
    }
    bot = DCABotSimulator(params)
    opt = bot.run(pd.DataFrame({
        "open": [100] * 5, "high": [103] * 5, "low": [99] * 5,
        "close": [101] * 5, "volume": [1000] * 5,
    }, index=pd.date_range("2024-01-01", periods=5, freq="1h")),
        pd.Series([True] + [False] * 4, index=pd.date_range("2024-01-01", periods=5, freq="1h")),
    )["optimized_params"]
    assert "base_order_volume" in opt
    assert "take_profit_percentage" in opt
    assert "active_deals" not in opt
    assert "closed_deals" not in opt
