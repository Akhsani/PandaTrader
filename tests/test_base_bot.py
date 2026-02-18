"""
Unit tests for base_bot utilities (FeeEngine, compute_bot_metrics).
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bots.base_bot import FeeEngine


def test_fee_engine_slippage():
    """Slippage increases buy cost and reduces sell proceeds."""
    engine = FeeEngine(fee=0.001, slippage_bps=10)  # 0.1% slippage
    buy_cost = engine.apply_buy_fee(100)
    sell_proceeds = engine.apply_sell_fee(100)
    # fee 0.1% + slippage 0.1% = 0.2% on each side
    assert abs(buy_cost - 100.2) < 0.01
    assert abs(sell_proceeds - 99.8) < 0.01


def test_fee_engine_no_slippage():
    """Default slippage_bps=0 preserves original behavior."""
    engine = FeeEngine(fee=0.001)
    assert engine.apply_buy_fee(100) == 100 * 1.001
    assert engine.apply_sell_fee(100) == 100 * 0.999
