"""Unit tests for strategies/WhaleAccumulation.py and backtest_strategy_8 (Strategy 8)"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np

from research.backtests.backtest_strategy_8 import (
    compute_synthetic_accumulation_signal,
    backtest_whale_accumulation,
    load_nansen_flows_or_synthetic,
)


@pytest.fixture
def sample_daily_ohlcv():
    np.random.seed(42)
    idx = pd.date_range('2024-01-01', periods=100, freq='1D')
    close = 100 + np.cumsum(np.random.randn(100) * 2)
    return pd.DataFrame({
        'open': close - 1,
        'high': close + 2,
        'low': close - 2,
        'close': close,
        'volume': np.random.rand(100) * 1e6 + 100000,
    }, index=idx)


def test_compute_synthetic_signal_returns_series(sample_daily_ohlcv):
    signal = compute_synthetic_accumulation_signal(sample_daily_ohlcv, lookback=7)
    assert isinstance(signal, pd.Series)
    assert len(signal) == len(sample_daily_ohlcv)
    assert signal.isin([0, 1]).all()


def test_compute_synthetic_signal_with_lookback(sample_daily_ohlcv):
    s7 = compute_synthetic_accumulation_signal(sample_daily_ohlcv, lookback=7)
    s14 = compute_synthetic_accumulation_signal(sample_daily_ohlcv, lookback=14)
    assert len(s7) == len(s14)


def test_compute_synthetic_signal_with_trend_filter():
    """Trend filter requires >=200 rows; with uptrend, signal may differ."""
    np.random.seed(42)
    idx = pd.date_range('2024-01-01', periods=250, freq='1D')
    close = 100 + np.cumsum(np.random.randn(250) * 0.5)  # Slight uptrend
    df = pd.DataFrame({
        'open': close - 1, 'high': close + 2, 'low': close - 2, 'close': close,
        'volume': np.random.rand(250) * 1e6 + 100000,
    }, index=idx)
    s_no_filter = compute_synthetic_accumulation_signal(df, lookback=7, use_trend_filter=False)
    s_with_filter = compute_synthetic_accumulation_signal(df, lookback=7, use_trend_filter=True)
    assert s_with_filter.sum() <= s_no_filter.sum()  # Trend filter never adds signals


def test_backtest_whale_accumulation_returns_dict(sample_daily_ohlcv):
    signal = compute_synthetic_accumulation_signal(sample_daily_ohlcv)
    result = backtest_whale_accumulation(sample_daily_ohlcv, signal, hold_days=7)
    assert result is not None
    assert 'total_return' in result
    assert 'apy' in result
    assert 'max_drawdown' in result
    assert 'trades' in result
    assert 'buy_hold_return' in result


def test_backtest_whale_accumulation_with_none_signal(sample_daily_ohlcv):
    result = backtest_whale_accumulation(sample_daily_ohlcv, None)
    assert result is None


def test_backtest_whale_accumulation_with_empty_df():
    result = backtest_whale_accumulation(pd.DataFrame(), pd.Series(dtype=float))
    assert result is None


def test_load_nansen_returns_tuple_when_no_api_key(sample_daily_ohlcv):
    """load_nansen_flows_or_synthetic returns (signal, source) tuple."""
    from utils.nansen_whale_tracker import NansenWhaleTracker
    tracker = NansenWhaleTracker()
    tracker.api_key = ''  # No key
    signal, source = load_nansen_flows_or_synthetic(
        'BTC/USDT', sample_daily_ohlcv, tracker, require_nansen=False
    )
    assert signal is not None
    assert source == 'synthetic'
    assert len(signal) == len(sample_daily_ohlcv)


def test_load_nansen_returns_none_when_require_nansen_and_no_data(sample_daily_ohlcv):
    """When require_nansen=True and no API key, returns (None, None)."""
    from utils.nansen_whale_tracker import NansenWhaleTracker
    tracker = NansenWhaleTracker()
    tracker.api_key = ''
    signal, source = load_nansen_flows_or_synthetic(
        'BTC/USDT', sample_daily_ohlcv, tracker, require_nansen=True
    )
    assert signal is None
    assert source is None


def test_backtest_strategy_8_import():
    """Verify backtest_strategy_8 module imports and has required functions."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "backtest_strategy_8",
        os.path.join(os.path.dirname(__file__), '..', 'research', 'backtests', 'backtest_strategy_8.py')
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'backtest_whale_accumulation')
    assert hasattr(mod, 'compute_synthetic_accumulation_signal')
    assert hasattr(mod, 'run')
