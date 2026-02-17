
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
    stoploss = -0.05       # 5% stop loss (wider for mean reversion)
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    
    minimal_roi = {
        "0": 0.05,
        "24": 0.02,
        "48": 0.01
    }

    # Strategy parameters
    funding_window = 24  # 24 hours rolling window for Z-Score
    z_score_threshold = 2.0
    adx_threshold = 25 # ADX > 25 implies trend, we want ADX < 25 for mean reversion
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Funding Rate Z-Score
        if 'funding_rate' in dataframe.columns:
            dataframe['funding_mean'] = dataframe['funding_rate'].rolling(window=self.funding_window).mean()
            dataframe['funding_std'] = dataframe['funding_rate'].rolling(window=self.funding_window).std()
            
            # Avoid division by zero
            dataframe['funding_zscore'] = (dataframe['funding_rate'] - dataframe['funding_mean']) / dataframe['funding_std']
        else:
            dataframe['funding_zscore'] = 0.0
            
        # 2. Market Regime (ADX)
        dataframe['adx'] = ta.ADX(dataframe)
            
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Long Entry: 
        # 1. Funding extremely negative (Shorts paying Longs) -> Z-Score < -2
        # 2. Market is not strongly trending (ADX < 25)
        dataframe.loc[
            (dataframe['funding_zscore'] < -self.z_score_threshold) &
            (dataframe['adx'] < self.adx_threshold) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
            
        # Short Entry: 
        # 1. Funding extremely positive (Longs paying Shorts) -> Z-Score > 2
        # 2. Market is not strongly trending (ADX < 25)
        dataframe.loc[
            (dataframe['funding_zscore'] > self.z_score_threshold) &
            (dataframe['adx'] < self.adx_threshold) &
            (dataframe['volume'] > 0),
            'enter_short'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit Long: Funding normalizes (Z-Score > -0.5)
        dataframe.loc[
            (dataframe['funding_zscore'] > -0.5) &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
            
        # Exit Short: Funding normalizes (Z-Score < 0.5)
        dataframe.loc[
            (dataframe['funding_zscore'] < 0.5) &
            (dataframe['volume'] > 0),
            'exit_short'] = 1
            
        return dataframe
