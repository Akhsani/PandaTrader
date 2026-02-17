# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401

# --- Do not remove these libs ---
import numpy as np
import pandas as pd
from pandas import DataFrame

from freqtrade.strategy import (BooleanParameter, CategoricalParameter, DecimalParameter,
                                IStrategy, IntParameter)

# --- Add your lib to import here ---
import talib.abstract as ta
import freqtrade.vendor.qtpylib.indicators as qtpylib
from strategies.base_strategy import BaseStrategy

class WeekendMomentum(BaseStrategy):
    """
    Strategy 1: Weekend Momentum Premium (v2 - Optimized)
    
    Hypothesis:
    Crypto returns on weekends (Sat-Sun) significantly exceed weekday returns.
    Enhanced with a Trend Filter (EMA50 > EMA200) AND Regime Gating.
    
    Optimizations v2:
    - Inherits BaseStrategy (Risk Manager + Regime Detector)
    - Stoploss tightened to -3% (from 5%)
    - Regime Gating: NO TRADES in 'BEAR' regime (Master Switch)
    """
    
    INTERFACE_VERSION = 3
    
    # ROI: We ideally exit on Monday, but take profit if lucky
    minimal_roi = {
        "0": 0.05, 
        "3": 0.03, 
    }

    # Optimization: Tightened from -0.05 to -0.03
    stoploss = -0.03

    # Trailing stop
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    startup_candle_count: int = 200
    timeframe = '1d'
    can_short = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Base Strategy Indicators (Regime Detection)
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # Trend Indicators
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Momentum & Volatility
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        # Volatility gate: only trade when ATR is below 75th percentile (avoid high-vol weekends)
        dataframe['atr_p75'] = dataframe['atr'].rolling(200).quantile(0.75)
        
        # Day of week (0=Monday, ... 4=Friday, ... 6=Sunday)
        dataframe['day_of_week'] = dataframe['date'].dt.dayofweek

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Logic:
        1. It is Friday
        2. Regime is NOT Bear (Master Switch)
        3. Long Term Trend is Bullish (EMA50 > EMA200)
        4. Volatility gate: ATR below 75th percentile (avoid high-vol weekends)
        """
        dataframe.loc[
            (
                # Entry on Friday (4)
                (dataframe['day_of_week'] == 4) &
                
                # REGIME MASTER SWITCH: No trades in Bear Market
                # This protects against "Weekend Crashes" in Bear Markets
                (dataframe['regime'] != 'BEAR') &
                
                # Trend Filter: EMA50 > EMA200 (Golden Cross / Bullish)
                (dataframe['ema50'] > dataframe['ema200']) &
                
                # ADX Filter: Trend strength > 20 (avoid weak trends)
                (dataframe['adx'] > 20) &
                
                # Volatility gate: only trade when ATR < 75th percentile (skip high-vol weekends)
                ((dataframe['atr'] < dataframe['atr_p75']) | dataframe['atr_p75'].isna()) &
                
                # Volume check
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Exit Logic:
        1. It is Monday
        """
        dataframe.loc[
            (
                # Exit on Monday (0)
                (dataframe['day_of_week'] == 0) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe
