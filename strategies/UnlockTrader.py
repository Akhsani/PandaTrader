import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class UnlockTrader:
    def __init__(self, unlock_data):
        self.unlocks = unlock_data
        
    def generate_signals(self, price_data, token_symbol, use_trend_filter=False):
        """
        Generates buy/sell signals based on unlock events.
        
        Strategy:
        1. Short/Exit 30 days before unlock if impact is negative.
           - FILTER: Do NOT short if in strong bull trend (ADX > 30 and Price > SMA200) if use_trend_filter=True.
        2. Long/Enter 14 days after unlock if impact is negative (expecting relief bounce/stabilization).
        """
        import talib
        
        signals = pd.Series(index=price_data.index, data=0) # 0: Hold, -1: Short/Exit, 1: Long/Enter
        
        # Calculate Indicators for Filter
        if use_trend_filter:
            close = price_data['close'].values
            high = price_data['high'].values
            low = price_data['low'].values
            
            # ADX for trend strength
            adx = talib.ADX(high, low, close, timeperiod=14)
            
            # SMA200 for trend direction
            sma200 = talib.SMA(close, timeperiod=200)
            
            # Bull Trend Condition: High ADX (>25) AND Price > SMA200
            # We want to AVOID shorting into this.
            is_bull_trend = (adx > 25) & (close > sma200)
            is_bull_trend = pd.Series(is_bull_trend, index=price_data.index).fillna(False)
        else:
            is_bull_trend = pd.Series(False, index=price_data.index)
        
        token_unlocks = self.unlocks[self.unlocks['symbol'] == token_symbol]
        
        for _, row in token_unlocks.iterrows():
            unlock_date = row['unlock_date']
            
            # Short Window: 30 days before
            short_start = unlock_date - timedelta(days=30)
            short_end = unlock_date - timedelta(days=1)
            
            # Long Window: 14 days after
            long_start = unlock_date + timedelta(days=14)
            long_end = unlock_date + timedelta(days=20) 
            
            # Check for overlapping data
            # If the short window is within our price data range
            if short_start in signals.index or short_end in signals.index:
                # Apply Short Signal via mask
                # Only short if NOT in bull trend
                mask = (signals.index >= short_start) & (signals.index <= short_end)
                
                if use_trend_filter:
                    # Filter out days where bull trend is active
                    trend_mask = is_bull_trend.reindex(signals.index).fillna(False)
                    final_mask = mask & (~trend_mask)
                    signals.loc[final_mask] = -1
                else:
                    signals.loc[mask] = -1
            
            # Mark Long Signals (Re-entry)
            # We generally take the relief bounce regardless of trend (or maybe only if NOT bear trend? Keep simple for now)
            signals.loc[long_start:long_end] = 1
            
        return signals

    def run_backtest(self, price_df, token_symbol):
        """
        Simple vector backtest.
        """
        signals = self.generate_signals(price_df, token_symbol)
        
        # Calculate returns
        # If Signal is -1, we are Short. If Signal is 1, we are Long. 0 is Cash.
        # Daily Return * Signal. (Shift signal by 1 to avoid lookahead bias - trade execution next day)
        
        asset_returns = price_df['close'].pct_change()
        strategy_returns = asset_returns * signals.shift(1)
        
        return strategy_returns.dropna()
