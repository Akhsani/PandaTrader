"""
Unit tests for Monte Carlo validators.
"""
import pytest
import pandas as pd
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidator, MonteCarloValidatorGrid


def test_monte_carlo_validator_compound():
    """MonteCarloValidator (compound) produces reasonable equity from pnl returns."""
    # 10 trades, each +2% return
    trades = pd.DataFrame({"pnl": [0.02] * 10})
    validator = MonteCarloValidator(trades, initial_capital=1000)
    stats, _ = validator.run_simulation(n_simulations=100)
    assert stats["median_final_equity"] > 1000
    assert stats["ruin_probability"] == 0
    assert stats["median_final_equity"] < 10000  # Sanity: not exploding


def test_monte_carlo_validator_grid_additive():
    """MonteCarloValidatorGrid uses additive returns; no compounding inflation."""
    # Grid: 20 cells, investment 1000, each pnl is return fraction per cell
    # Simulate 100 trades with small positive returns
    n_trades = 100
    capital_per_trade = 1000 / 20  # 50
    trades = pd.DataFrame({"pnl": [0.01] * n_trades})  # 1% per cell
    validator = MonteCarloValidatorGrid(
        trades, initial_capital=1000, investment_amount=1000, grid_lines_count=20
    )
    stats, _ = validator.run_simulation(n_simulations=100)
    # Additive: 100 * 0.01 * 50 = 50 profit, equity ~1050
    assert 1000 < stats["median_final_equity"] < 2000
    assert stats["ruin_probability"] < 0.5
    # Critical: must NOT be billions (old compounding bug)
    assert stats["median_final_equity"] < 100000


def test_monte_carlo_grid_vs_compound():
    """Grid validator produces lower equity than compound for same pnl (no inflation)."""
    trades = pd.DataFrame({"pnl": [0.005] * 500})  # 500 trades, 0.5% each
    compound_validator = MonteCarloValidator(trades, initial_capital=1000)
    grid_validator = MonteCarloValidatorGrid(
        trades, initial_capital=1000, investment_amount=1000, grid_lines_count=20
    )
    compound_stats, _ = compound_validator.run_simulation(n_simulations=50)
    grid_stats, _ = grid_validator.run_simulation(n_simulations=50)
    # Compound: (1.005)^500 ~12k. Grid: additive 500*0.005*50=125 profit ~1125. Grid << compound.
    assert grid_stats["median_final_equity"] < compound_stats["median_final_equity"]
