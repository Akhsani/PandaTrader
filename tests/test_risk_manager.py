"""Unit tests for utils/risk_manager.py"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from utils.risk_manager import RiskManager


@pytest.fixture
def risk_manager():
    return RiskManager({
        'max_risk_per_trade': 0.01,
        'max_daily_loss': 0.03,
        'max_portfolio_drawdown': 0.15,
        'initial_capital': 10000.0
    })


def test_trade_allowed_initially(risk_manager):
    assert risk_manager.check_trade_allowed('BTC/USDT', 'Strategy1') is True


def test_position_size_calculation(risk_manager):
    entry, stop = 50000, 49000
    qty = risk_manager.calculate_position_size(entry, stop)
    assert qty > 0
    assert qty * entry <= risk_manager.current_capital * 0.20


def test_position_size_zero_for_invalid_prices(risk_manager):
    assert risk_manager.calculate_position_size(0, 49000) == 0.0
    assert risk_manager.calculate_position_size(50000, 0) == 0.0
    assert risk_manager.calculate_position_size(50000, 50000) == 0.0


def test_daily_loss_limit_blocks_trade(risk_manager):
    rm = RiskManager({
        'max_risk_per_trade': 0.01,
        'max_daily_loss': 0.03,
        'initial_capital': 10000.0
    })
    rm.record_trade_result(-400)  # -4% on 10k
    assert rm.check_trade_allowed('BTC/USDT', 'S1') is False


def test_kill_switch_on_drawdown(risk_manager):
    rm = RiskManager({
        'max_risk_per_trade': 0.01,
        'max_daily_loss': 0.03,
        'max_portfolio_drawdown': 0.15,
        'initial_capital': 10000.0
    })
    rm.update_capital(8400)  # 16% drawdown
    assert rm.is_kill_switch_active is True
    assert rm.check_trade_allowed('BTC/USDT', 'S1') is False
