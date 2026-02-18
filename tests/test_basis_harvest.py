"""Unit tests for Strategy 6 Basis Harvesting (Phase 2C)"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np


def test_z_to_risk():
    from utils.funding_utils import z_to_risk
    assert z_to_risk(1.5) == 0.005
    assert z_to_risk(2.0) == 0.01
    assert z_to_risk(2.5) == 0.015
    assert z_to_risk(3.0) == 0.015


def test_basis_calculation():
    """Basis = (spot - perp) / perp"""
    spot = pd.Series([100, 101, 102])
    perp = pd.Series([99.5, 100.5, 101])
    basis = (spot - perp) / perp
    assert basis.iloc[0] == pytest.approx(0.005025, rel=1e-3)


def test_backtest_strategy_6_import():
    """Ensure backtest module loads"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "backtest_strategy_6",
        os.path.join(os.path.dirname(__file__), '..', 'research', 'backtests', 'backtest_strategy_6.py')
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, 'backtest_basis_harvest')
