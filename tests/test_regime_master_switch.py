"""Unit tests for Regime Master Switch (Phase 2B.1)"""
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


def test_set_regime(risk_manager):
    risk_manager.set_regime('BULL')
    assert risk_manager.current_regime == 'BULL'
    risk_manager.set_regime('bear')
    assert risk_manager.current_regime == 'BEAR'


def test_is_strategy_allowed_bull(risk_manager):
    risk_manager.set_regime('BULL')
    assert risk_manager.is_strategy_allowed('WeekendMomentum', 'long') is True
    assert risk_manager.is_strategy_allowed('FundingReversion', 'long') is True
    assert risk_manager.is_strategy_allowed('FundingReversion', 'short') is False
    assert risk_manager.is_strategy_allowed('RegimeGrid', 'long') is False


def test_is_strategy_allowed_bear(risk_manager):
    risk_manager.set_regime('BEAR')
    assert risk_manager.is_strategy_allowed('WeekendMomentum', 'long') is False
    assert risk_manager.is_strategy_allowed('FundingReversion', 'short') is True
    assert risk_manager.is_strategy_allowed('FundingReversion', 'long') is False


def test_is_strategy_allowed_sideways(risk_manager):
    risk_manager.set_regime('SIDEWAYS')
    assert risk_manager.is_strategy_allowed('FundingReversion', 'long') is True
    assert risk_manager.is_strategy_allowed('FundingReversion', 'short') is True
    assert risk_manager.is_strategy_allowed('RegimeGrid', 'long') is True


def test_position_size_multiplier_transition(risk_manager):
    risk_manager.set_regime('TRANSITION')
    assert risk_manager.get_position_size_multiplier() == 0.5


def test_position_size_multiplier_bear_s5(risk_manager):
    risk_manager.set_regime('BEAR')
    assert risk_manager.get_position_size_multiplier('RegimeGrid') == 0.5


def test_position_size_multiplier_normal(risk_manager):
    risk_manager.set_regime('BULL')
    assert risk_manager.get_position_size_multiplier() == 1.0
