# Strategies/FundingReversion.py
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
import numpy as np

from base_strategy import BaseStrategy

class FundingReversion(BaseStrategy):
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
    
    # Risk settings (Strategy specific overrides)
    stoploss = -0.05
    custom_risk_per_trade = 0.0025 # 0.25% Risk per trade (High Frequency/Reversion)
    
    # Strategy parameters
    buy_params = {
        "z_score_threshold": 1.5,
        "adx_threshold": 30
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Base Strategy Indicators (Regime Detection)
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # 2. Funding Rates (simulated for backtest if not Present)
        # In Freqtrade live, this comes from data provider.
        if 'funding_rate' not in dataframe.columns:
            dataframe['funding_rate'] = 0.0 # Placeholder
            
        # Z-Score of Funding Rate (Rolling 24h)
        dataframe['funding_mean'] = dataframe['funding_rate'].rolling(24).mean()
        dataframe['funding_std'] = dataframe['funding_rate'].rolling(24).std()
        dataframe['funding_zscore'] = (dataframe['funding_rate'] - dataframe['funding_mean']) / dataframe['funding_std']
        
        # ADX for Trend Filtering
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Logic with Regime Gating
        """
        
        # LONG Entry:
        # 1. Funding is extremely negative (Short Squeeze potential)
        # 2. Market is NOT in 'BEAR' regime (Master Switch)
        # 3. ADX is low (Mean Reversion works best in chop)
        
        dataframe.loc[
            (dataframe['funding_zscore'] < -self.buy_params['z_score_threshold']) &
            (dataframe['regime'] != 'BEAR') &  # <--- REGIME MASTER SWITCH
            (dataframe['adx'] < self.buy_params['adx_threshold']) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
            
        # SHORT Entry:
        # 1. Funding is extremely positive (Long Squeeze potential)
        # 2. Market is NOT in 'BULL' regime? (Optional, maybe we allow shorts in Bull if funding is crazy)
        # Let's be safe: Don't short in Strong Bull.
        
        dataframe.loc[
            (dataframe['funding_zscore'] > self.buy_params['z_score_threshold']) &
            (dataframe['regime'] != 'BULL') & 
            (dataframe['adx'] < self.buy_params['adx_threshold']) &
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
