# strategies/BasisHarvest.py
"""
Strategy 6: Spot-Perp Basis Harvesting (Delta-Neutral Funding Carry)
Phase 2C - Long spot, short perp, collect 8-hour funding.
Regime guard: Only in BEAR or SIDEWAYS (never BULL - short gamma risk).
"""
from pandas import DataFrame
import pandas as pd
import numpy as np
import logging

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class BasisHarvest(BaseStrategy):
    """
    Basis Harvesting: Long spot + short perp, collect funding.
    Only active in BEAR or SIDEWAYS regimes.
    """
    INTERFACE_VERSION = 3
    timeframe = '8h'  # Funding period
    can_short = True
    
    stoploss = -0.02  # Tight - delta neutral
    custom_risk_per_trade = 0.005  # 0.5%
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)
        
        if 'funding_rate' not in dataframe.columns:
            dataframe['funding_rate'] = 0.0
        
        # Basis inversion: 3 consecutive negative funding periods
        neg = (dataframe['funding_rate'] < 0).astype(int)
        dataframe['neg_streak_3'] = (neg + neg.shift(1) + neg.shift(2)) >= 3
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Regime guard: Only BEAR or SIDEWAYS (never BULL)
        regime_ok = (dataframe['regime'] == 'BEAR') | (dataframe['regime'] == 'SIDEWAYS')
        
        # Entry: Positive funding (we receive as short perp). Fine-tuned: 0.00005 (EXP_FineTuning_Results)
        dataframe.loc[
            regime_ok &
            (dataframe['funding_rate'] > 0.00005) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
        
        # For basis harvest we're long spot + short perp. Freqtrade typically does one leg.
        # This strategy assumes perp trading; long = synthetic long spot + short perp via funding.
        dataframe.loc[
            regime_ok &
            (dataframe['funding_rate'] > 0.00005) &
            (dataframe['volume'] > 0),
            'enter_short'] = 0  # No standalone short
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit: 3 consecutive negative funding (basis inversion)
        dataframe.loc[
            dataframe['neg_streak_3'] &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
        return dataframe

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: str, entry_tag: str,
                            side: str, **kwargs) -> bool:
        # Block in BULL regime
        if self.risk_manager.current_regime == 'BULL':
            logger.warning("BasisHarvest: Blocked in BULL regime (short gamma risk)")
            return False
        return super().confirm_trade_entry(pair, order_type, amount, rate,
                                           time_in_force, current_time, entry_tag, side, **kwargs)
