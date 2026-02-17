"""Unit tests for utils/regime_detector.py"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import pytest
from utils.regime_detector import CryptoRegimeDetector


@pytest.fixture
def sample_price_df():
    np.random.seed(42)
    n = 300
    returns = np.random.randn(n).cumsum() * 0.01
    close = 100 * (1 + returns)
    return pd.DataFrame({
        'open': close - 0.5,
        'high': close + 1,
        'low': close - 1,
        'close': close,
        'volume': np.random.randint(1000, 10000, n)
    })


def test_fit_requires_min_data():
    det = CryptoRegimeDetector()
    short_df = pd.DataFrame({'open': [1]*50, 'high': [2]*50, 'low': [0]*50, 'close': [1]*50, 'volume': [1]*50})
    result = det.fit(short_df)
    assert result is None


def test_fit_returns_df(sample_price_df):
    det = CryptoRegimeDetector()
    result = det.fit(sample_price_df)
    assert result is not None
    assert 'regime_label' in result.columns
    assert set(result['regime_label'].unique()) & {'BEAR', 'BULL', 'SIDEWAYS', 'TRANSITION'}


def test_predict_requires_fit(sample_price_df):
    det = CryptoRegimeDetector()
    with pytest.raises(ValueError, match="fit"):
        det.predict(sample_price_df)


def test_predict_after_fit(sample_price_df):
    det = CryptoRegimeDetector()
    det.fit(sample_price_df)
    # predict needs enough rows for indicators (SMA200, etc.)
    out = det.predict(sample_price_df)
    assert 'regime_label' in out.columns
    assert len(out) > 0
