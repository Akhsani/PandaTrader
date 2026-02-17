from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from utils.regime_detector import CryptoRegimeDetector
except ImportError:
    # Fallback or mock for initial loading if utils not found
    print("WARNING: Could not import CryptoRegimeDetector. Grid logic will be disabled.")
    CryptoRegimeDetector = None

class RegimeGrid(IStrategy):
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
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.regime_detector = CryptoRegimeDetector() if CryptoRegimeDetector else None
        self.is_fitted = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Calculate features for Detector (ADX, ATR, etc handled inside Detector)
        # But we need basic columns? Detector handles it.
        
        # 2. Train HMM on available data
        if self.regime_detector and not self.is_fitted:
             self.regime_detector.fit(dataframe)
             self.is_fitted = True
        
        if self.regime_detector and self.is_fitted:
            df_regime = self.regime_detector.predict(dataframe)
            dataframe['regime'] = df_regime['regime_label']
        else:
            dataframe['regime'] = 'UNKNOWN'
            
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Grid Entry Logic (Static %):
        - Regime == SIDEWAYS
        - Price < Center - Spacing -> Buy dip
        """
        
        # Center line (24h rolling mean)
        dataframe['center'] = dataframe['close'].rolling(24).mean()
        
        # Static Bands
        dataframe['lower_band'] = dataframe['center'] * (1 - self.grid_spacing)
        dataframe['upper_band'] = dataframe['center'] * (1 + self.grid_spacing)
        
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
