"""Unit tests for utils/backtest_utils.py"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd
import pytest
from utils.backtest_utils import calculate_net_returns, get_performance_metrics


def test_calculate_net_returns_reduces_returns():
    n = 100
    returns = pd.Series(np.random.randn(n) * 0.01)
    signals = pd.Series(0, index=returns.index)
    signals.iloc[10:50] = 1
    signals.iloc[50:80] = -1
    net = calculate_net_returns(returns, signals)
    assert (net <= returns + 0.001).all()


def test_get_performance_metrics_empty():
    assert get_performance_metrics(pd.Series(dtype=float)) == {}


def test_get_performance_metrics_basic():
    returns = pd.Series([0.01, -0.005, 0.02, 0.01])
    m = get_performance_metrics(returns)
    assert 'total_return' in m
    assert 'sharpe' in m
    assert 'max_drawdown' in m
    assert m['total_return'] > 0
