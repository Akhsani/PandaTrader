"""
Unit tests for base_bot utilities (FeeEngine, compute_bot_metrics, compute_per_deal_ev, compute_annualized_capital_return).
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bots.base_bot import FeeEngine, compute_per_deal_ev, compute_annualized_capital_return


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


def test_compute_per_deal_ev():
    """EV = mean(TP returns) × win_rate + mean(SL returns) × loss_rate."""
    closed_deals = [
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": 0.025, "exit_reason": "take_profit"},
        {"pnl": -0.15, "exit_reason": "stop_loss"},
    ]
    ev = compute_per_deal_ev(closed_deals)
    win_rate = 8 / 9
    loss_rate = 1 / 9
    mean_tp = 0.025
    mean_sl = -0.15
    expected = mean_tp * win_rate + mean_sl * loss_rate
    assert abs(ev - expected) < 1e-6
    assert ev > 0


def test_compute_per_deal_ev_empty():
    """Empty deals returns 0."""
    assert compute_per_deal_ev([]) == 0.0
    assert compute_per_deal_ev([{"other": 1}]) == 0.0


def test_compute_annualized_capital_return():
    """Formula: (total_profit / initial_capital) / years * 100."""
    # 10% profit on 1000 over 1 year = 10% annualized
    ret = compute_annualized_capital_return(100, 1000, 1.0)
    assert abs(ret - 10.0) < 0.01


def test_compute_annualized_capital_return_zero_years():
    """Zero or negative years returns 0."""
    assert compute_annualized_capital_return(100, 1000, 0) == 0.0
    assert compute_annualized_capital_return(100, 1000, -1) == 0.0
