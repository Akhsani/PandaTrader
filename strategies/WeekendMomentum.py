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

class WeekendMomentum(IStrategy):
    """
    Strategy 1: Weekend Momentum Premium
    
    Hypothesis:
    Crypto returns on weekends (Sat-Sun) significantly exceed weekday returns.
    Enhanced with a Trend Filter (EMA50 > EMA200) to avoid trading in bear markets.
    
    Setup:
    - Timeframe: 1d
    - Entry: Friday Close (implied by checking if today is Friday and trend is bullish)
    - Exit: Monday Close (implied by checking if today is Monday)
    
    """
    
    # Strategy interface version - allow new iterations of the strategy interface.
    # Check the documentation or the Sample strategy to get the latest version.
    INTERFACE_VERSION = 3

    # Minimal ROI designed for the strategy.
    # We are not using ROI here, we exit based on time (Monday).
    # But Freqtrade requires this dict. We set it to something high to avoid interference,
    # or low if we want to scalp. The playbook suggests time-based exit.
    # However, playbook had: minimal_roi = {"0": 0.05, "3": 0.02}
    minimal_roi = {
        "0": 0.05, # 5% profit - take it
        "3": 0.02, # 2% profit after 3 days
        "7": 0.01  # 1% profit after 7 days
    }

    # Optimal stoploss designed for the strategy.
    # Playbook: stoploss = -0.03 (3%)
    stoploss = -0.03

    # Trailing stop:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02
    trailing_only_offset_is_reached = True

    # Run "populate_indicators" on the startup period (e.g. 200 candles for EMA200)
    startup_candle_count: int = 200

    # Calculated timeframe
    timeframe = '1d'

    # Can this strategy go short?
    can_short = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Adds several different TA indicators to the given DataFrame
        """
        # Trend Indicators
        dataframe['ema50'] = ta.EMA(dataframe, timeperiod=50)
        dataframe['ema200'] = ta.EMA(dataframe, timeperiod=200)
        
        # Momentum & Volatility
        dataframe['adx'] = ta.ADX(dataframe)
        dataframe['atr'] = ta.ATR(dataframe)
        
        # Day of week (0=Monday, 6=Sunday)
        # Note: Freqtrade dataframe 'date' column is datetime
        dataframe['day_of_week'] = dataframe['date'].dt.dayofweek

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the entry signal for the given dataframe
        """
        dataframe.loc[
            (
                # Entry on Friday (4)
                (dataframe['day_of_week'] == 4) &
                # Trend Filter: EMA50 > EMA200 (Golden Cross / Bullish)
                (dataframe['ema50'] > dataframe['ema200']) &
                # ADX Filter: Trend strength > 20 (avoid weak trends)
                (dataframe['adx'] > 20) &
                # Volatility Filter: Avoid extreme volatility (ATR / Close < 0.05 i.e. 5% daily move)
                ((dataframe['atr'] / dataframe['close']) < 0.05) &
                # Volume check (optional, basic sanity)
                (dataframe['volume'] > 0)
            ),
            'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Based on TA indicators, populates the exit signal for the given dataframe
        """
        dataframe.loc[
            (
                # Exit on Monday (0)
                (dataframe['day_of_week'] == 0) &
                (dataframe['volume'] > 0)
            ),
            'exit_long'] = 1

        return dataframe
