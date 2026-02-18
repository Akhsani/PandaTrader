from pandas import DataFrame
import pandas as pd
import numpy as np
import sys
import os

# Add possible paths for utils module (container: /freqtrade, local: project root)
for p in ['/freqtrade', os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]:
    if p not in sys.path:
        sys.path.insert(0, p)

from base_strategy import BaseStrategy


class RegimeGrid(BaseStrategy):
    """
    Regime-Adaptive Grid Strategy
    - Detects market regime (Bull, Bear, Sideways) using HMM
    - Deploys Grid Bot logic ONLY during 'SIDEWAYS' regime
    - Uses tight stop-loss or trend-following exit during 'TREND' regimes
    """
    INTERFACE_VERSION = 3
    
    # minimal_roi = {
    #     "0": 0.01,    # 1% profit in grid mode is good
    # }
    
    # Grid settings
    # Static Grid (v1 Logic - Proven safer)
    grid_spacing = 0.005 # 0.5% spacing
    grid_levels = 10
    
    stoploss = -0.05
    timeframe = '1h'
    can_short = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Base Strategy: Regime Detection (Phase 2B.6 - Master Switch)
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # 2. Grid bands (center, lower, upper)
        dataframe['center'] = dataframe['close'].rolling(24).mean()
        dataframe['lower_band'] = dataframe['center'] * (1 - self.grid_spacing)
        dataframe['upper_band'] = dataframe['center'] * (1 + self.grid_spacing)
            
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Grid Entry Logic (Static %):
        - Regime == SIDEWAYS (Master Switch blocks in BULL)
        - Price < Center - Spacing -> Buy dip
        """
        # Enter Long if:
        # 1. Regime is SIDEWAYS
        # 2. Price is below lower band
        
        dataframe.loc[
            (dataframe['regime'] == 'SIDEWAYS') &
            (dataframe['close'] < dataframe['lower_band']) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit Logic:
        - Trend Exit: If Regime switches to BEAR, sell immediately.
        - Grid Profit: Sale at Upper Band
        """
        
        dataframe.loc[
            (
                (dataframe['regime'] == 'BEAR') | 
                ((dataframe['regime'] == 'SIDEWAYS') & (dataframe['close'] > dataframe['upper_band']))
            ) &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
            
        return dataframe
