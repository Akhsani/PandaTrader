
# Strategies/FundingReversion.py
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd
import numpy as np

class FundingReversion(IStrategy):
    """
    Funding Rate Mean Reversion Strategy
    
    Hypothesis: 
    When funding rates hit extremes (>0.05% or <-0.05%), they mean-revert.
    - Extreme Positive Funding -> Short
    - Extreme Negative Funding -> Long
    
    Note: Requires funding rate data. Freqtrade support for funding rates in backtesting 
    depends on data availability and configuration. This strategy assumes 'funding_rate' 
    column is available in dataframe (custom data or future support).
    """
    INTERFACE_VERSION = 3
    timeframe = '1h' # Using 1h to capture funding moves better than 1d
    can_short = True
    
    # Risk management
    stoploss = -0.02
    trailing_stop = True
    trailing_stop_positive = 0.005
    trailing_stop_positive_offset = 0.015
    
    minimal_roi = {
        "0": 0.05,
        "60": 0.02,
        "120": 0.0
    }

    # Strategy parameters
    funding_entry_threshold = 0.0005 # 0.05%
    funding_exit_threshold = 0.0001  # 0.01%
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Check if funding info is available. 
        # In live/dry-run, we might need to fetch it or it comes in info.
        # For backtesting, we assume it's loaded as a column or we can't really test it easily here.
        
        # Placeholder for funding rate if not present (to prevent errors if run without data)
        if 'funding_rate' not in dataframe.columns:
            dataframe['funding_rate'] = 0.0
            
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long Entry: Funding extremely negative (Shorts paying Longs)
        dataframe.loc[
            (dataframe['funding_rate'] < -self.funding_entry_threshold) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
            
        # Short Entry: Funding extremely positive (Longs paying Shorts)
        dataframe.loc[
            (dataframe['funding_rate'] > self.funding_entry_threshold) &
            (dataframe['volume'] > 0),
            'enter_short'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit Long: Funding normalizes
        dataframe.loc[
            (dataframe['funding_rate'].abs() < self.funding_exit_threshold) &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
            
        # Exit Short: Funding normalizes
        dataframe.loc[
            (dataframe['funding_rate'].abs() < self.funding_exit_threshold) &
            (dataframe['volume'] > 0),
            'exit_short'] = 1
            
        return dataframe
