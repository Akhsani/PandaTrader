
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to allow importing utils if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LiquidationMonitor:
    def __init__(self):
        self.cascade_threshold_dump = -0.05  # -5% drop
        self.funding_flip_threshold = -0.0001  # -0.01% funding rate (negative)
        
    def detect_cascades(self, price_df, funding_df):
        """
        Detects potential liquidation cascades based on:
        1. 24h Price Drop > 8%
        2. Funding Rate < -0.01% (indicating fear/short squeeze potential)
        """
        # Ensure indices are datetime and sorted
        price_df = price_df.sort_index()
        funding_df = funding_df.sort_index()
        
        # Resample funding to hourly to match price (ffill)
        funding_hourly = funding_df['fundingRate'].resample('1h').ffill()
        
        # Merge
        df = price_df.join(funding_hourly, how='inner')
        
        # Calculate 24h rolling return
        df['ret_24h'] = df['close'].pct_change(24)
        
        # Detect conditions
        df['is_crash'] = df['ret_24h'] < self.cascade_threshold_dump
        df['neg_funding'] = df['fundingRate'] < self.funding_flip_threshold
        
        # Signal: Crash + Negative Funding
        df['cascade_signal'] = df['is_crash'] & df['neg_funding']
        
        print(f"Debug Stats:")
        print(f"Min 24h Return: {df['ret_24h'].min():.4%}")
        print(f"Min Funding Rate: {df['fundingRate'].min():.6%}")
        print(f"Count < -5% Drop: {(df['ret_24h'] < -0.05).sum()}")
        print(f"Count Negative Funding: {(df['fundingRate'] < 0).sum()}")
        
        return df

def backtest_cascade_bounce(symbol='BTC_USDT'):
    # file paths
    ohlcv_path = f"data/ohlcv/{symbol}_1h.csv"
    funding_path = f"data/funding_rates/{symbol}_USDT_funding.csv"
    
    if not os.path.exists(ohlcv_path) or not os.path.exists(funding_path):
        print(f"Data not found for {symbol}. Run utils/fetch_1h_data.py first.")
        return

    # Load Data
    print(f"Loading data for {symbol}...")
    try:
        price_df = pd.read_csv(ohlcv_path, index_col='datetime', parse_dates=True)
        funding_df = pd.read_csv(funding_path, index_col='datetime', parse_dates=True)
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    monitor = LiquidationMonitor()
    df = monitor.detect_cascades(price_df, funding_df)
    
    signals = df[df['cascade_signal']]
    print(f"Detected {len(signals)} cascade signal hours.")
    
    # Consolidate signals (avoid multiple entries for same event)
    # Logic: If we are already in a trade, ignore new signals.
    # Logic 2: Group consecutive signals into one "event"
    
    events = []
    last_event_time = pd.Timestamp('2020-01-01')
    
    # Debug: Check Aug 5 2024
    if pd.Timestamp('2024-08-05') in df.index:
        print("--- Debug Aug 5 2024 ---")
        debug_slice = df.loc['2024-08-04':'2024-08-06']
        print(f"Min 24h Return in window: {debug_slice['ret_24h'].min():.4%}")
        print(f"Min Funding Rate in window: {debug_slice['fundingRate'].min():.6%}")
        # print(debug_slice[['close', 'ret_24h', 'fundingRate', 'is_crash', 'neg_funding']])
        print("------------------------")
    
    trades = []
    
    # Simulation Loop
    in_position = False
    entry_price = 0
    stop_loss = 0
    take_profit = 0
    entry_time = None
    
    # We iterate through the whole DF to simulate properly
    for current_time, row in df.iterrows():
        
        # 1. Manage existing position
        if in_position:
            # Check for fill
            low = row['low']
            high = row['high']
            
            # Check Stop Loss first (conservative)
            if low <= stop_loss:
                # Stopped out
                pnl = (stop_loss - entry_price) / entry_price
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_time,
                    'entry_price': entry_price,
                    'exit_price': stop_loss,
                    'pnl': pnl,
                    'result': 'stop_loss'
                })
                in_position = False
                continue
                
            # Check Take Profit
            if high >= take_profit:
                pnl = (take_profit - entry_price) / entry_price
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_time,
                    'entry_price': entry_price,
                    'exit_price': take_profit,
                    'pnl': pnl,
                    'result': 'take_profit'
                })
                in_position = False
                continue
            
            # Time exit (e.g., if strictly holding for X time, but here we use targets)
            # Optional: Time-based exit if stuck for 7 days
            if (current_time - entry_time).days >= 7:
                 exit_price = row['close']
                 pnl = (exit_price - entry_price) / entry_price
                 trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_time,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'result': 'time_exit'
                })
                 in_position = False
                 continue

        # 2. Look for Entry
        if not in_position and row['cascade_signal']:
            # Signal detected!
            # Filter: Wait for 4h green candle?
            # Simplified: Enter if previous candle was green? Or just enter now?
            # Strategy says: "Entry: close of first green 4hr candle"
            
            # Let's check if THIS candle is green (close > open)
            is_green = row['close'] > row['open']
            
            # To be strict about "4h green candle", we'd need to resample 4h.
            # Approximation on 1h: Enter if we have a strong 1h green candle OR cumulative green.
            # Let's just use the 1h green candle for now to test sensitivity.
            
            if is_green:
                # Check cooldown from last event to avoid over-trading same crash
                if (current_time - last_event_time).days < 2:
                    continue
                
                # Setup Trade
                cascade_low = row['low'] # Approximation of recent low
                # Ideally we look back 24h for the low
                lookback_window = df.loc[current_time - timedelta(hours=24):current_time]
                cascade_low = lookback_window['low'].min()
                cascade_high = lookback_window['high'].max() # Pre-cascade high approximation
                
                entry_price = row['close']
                stop_loss = cascade_low * 0.98 # 2% below low
                
                # Check if we are too late (price > 5% above low)
                if (entry_price - cascade_low) / cascade_low > 0.05:
                    # print(f"Skipped {entry_time}: Too late ({(entry_price - cascade_low) / cascade_low:.2%})")
                    continue

                # Target: 50% retracement of the dump
                take_profit = cascade_low + ((cascade_high - cascade_low) * 0.5)
                
                # Risk Management Calculation
                reward = take_profit - entry_price
                risk = entry_price - stop_loss
                
                if risk <= 0:
                    continue
                    
                rr_ratio = reward / risk
                
                # Filter by R:R
                if rr_ratio < 1.5:
                    # print(f"Skipped {entry_time}: Bad R:R ({rr_ratio:.2f})")
                    continue
                    
                entry_time = current_time
                in_position = True
                last_event_time = current_time
                
                print(f"Entering Long at {entry_time}: {entry_price:.2f} (Target: {take_profit:.2f}, Stop: {stop_loss:.2f}, R:R: {rr_ratio:.2f})")

    # Analyze Results
    if not trades:
        print("No trades generated.")
        return

    trades_df = pd.DataFrame(trades)
    
    print("\n--- Backtest Results ---")
    print(trades_df)
    
    total_trades = len(trades_df)
    win_rate = (trades_df['pnl'] > 0).mean()
    avg_pnl = trades_df['pnl'].mean()
    total_return = (1 + trades_df['pnl']).prod() - 1
    
    print(f"\nTotal Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Avg PnL: {avg_pnl:.2%}")
    print(f"Total Return: {total_return:.2%}")
    
    return trades_df

if __name__ == "__main__":
    backtest_cascade_bounce('BTC_USDT')
    backtest_cascade_bounce('ETH_USDT')
    backtest_cascade_bounce('SOL_USDT')
