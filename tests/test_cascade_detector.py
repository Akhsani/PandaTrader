"""Unit tests for utils/cascade_detector.py (Phase 2B.5)"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from utils.cascade_detector import detect_cascade, cascade_fires_now


@pytest.fixture
def sample_ohlcv():
    np.random.seed(42)
    idx = pd.date_range('2024-01-01', periods=200, freq='1h')
    close = 100 + np.cumsum(np.random.randn(200) * 0.5)
    return pd.DataFrame({
        'open': close - 0.5,
        'high': close + 1,
        'low': close - 1,
        'close': close,
        'volume': np.random.rand(200) * 1000 + 100
    }, index=idx)


def test_detect_cascade_returns_series(sample_ohlcv):
    result = detect_cascade(sample_ohlcv)
    assert isinstance(result, pd.Series)
    assert len(result) == len(sample_ohlcv)
    assert result.dtype == bool


def test_cascade_fires_now_empty():
    assert cascade_fires_now(None) is False
    assert cascade_fires_now(pd.DataFrame()) is False


def test_cascade_fires_now_short_df():
    df = pd.DataFrame({'close': [100], 'volume': [100], 'high': [101], 'low': [99]})
    # Too short for RSI
    assert cascade_fires_now(df) is False


def test_detect_cascade_with_oversold(sample_ohlcv):
    # Force RSI < 30 and vol spike on last row
    sample_ohlcv.loc[sample_ohlcv.index[-1], 'close'] = sample_ohlcv['close'].iloc[-2] * 0.95
    sample_ohlcv.loc[sample_ohlcv.index[-1], 'volume'] = 5000  # Spike
    result = detect_cascade(sample_ohlcv)
    assert isinstance(result, pd.Series)
