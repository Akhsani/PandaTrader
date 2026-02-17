import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class UnlockTrader:
    def __init__(self, unlock_data):
        self.unlocks = unlock_data
        
    def generate_signals(self, price_data, token_symbol, use_trend_filter=False):
        """
        Generates buy/sell signals based on unlock events.
        Returns a DataFrame with columns: ['signal', 'size_multiplier']
        """
        import talib
        
        # Initialize DataFrame
        results = pd.DataFrame(index=price_data.index)
        results['signal'] = 0
        results['size_multiplier'] = 1.0
        
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
            
            # SHORT SIGNALS
            if short_start in results.index or short_end in results.index:
                mask = (results.index >= short_start) & (results.index <= short_end)
                if use_trend_filter:
                    # Filter out days where bull trend is active (Don't short bull)
                    trend_mask = is_bull_trend.reindex(results.index).fillna(False)
                    final_mask = mask & (~trend_mask)
                    results.loc[final_mask, 'signal'] = -1
                else:
                    results.loc[mask, 'signal'] = -1
            
            # LONG SIGNALS (Relief Bounce)
            # Re-enter long after unlock.
            # Graduated Sizing: If Bull Trend, increase size by 50%
            
            long_mask = (results.index >= long_start) & (results.index <= long_end)
            results.loc[long_mask, 'signal'] = 1
            
            # Apply Sizing Multiplier for Longs in Bull Trend
            if use_trend_filter:
                bull_rows = long_mask & is_bull_trend
                results.loc[bull_rows, 'size_multiplier'] = 1.5
            
        return results

    def run_backtest(self, price_df, token_symbol):
        """
        Simple vector backtest.
        """
        results_df = self.generate_signals(price_df, token_symbol, use_trend_filter=True)
        signals = results_df['signal']
        sizes = results_df['size_multiplier']
        
        # Calculate returns
        # Return = Asset Return * Signal (shifted) * Size Multiplier (shifted)
        
        asset_returns = price_df['close'].pct_change()
        strategy_returns = asset_returns * signals.shift(1) * sizes.shift(1)
        
        return strategy_returns.dropna()
