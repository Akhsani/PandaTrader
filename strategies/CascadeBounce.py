
import pandas as pd
import numpy as np
import talib
import os
import sys

# Add parent directory to path to allow importing utils if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.data_loader import load_ohlcv

def backtest_cascade_bounce(symbol='BTC_USDT'):
    # file paths
    ohlcv_path = f"data/ohlcv/{symbol}_1h.csv"
    
    if not os.path.exists(ohlcv_path):
        print(f"Data not found for {symbol}. Run utils/fetch_1h_data.py first.")
        return

    # Load Data (load_ohlcv handles datetime/date column flexibility)
    print(f"Loading data for {symbol}...")
    try:
        df = load_ohlcv(ohlcv_path)
        df = df.sort_index()
    except Exception as e:
        print(f"Error loading data: {e}")
        return

    # --- INDICATORS ---
    # 1. RSI
    df['rsi'] = talib.RSI(df['close'], timeperiod=14)
    
    # 2. ATR
    df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
    
    # 3. EMA for Trend/Entry
    df['ema9'] = talib.EMA(df['close'], timeperiod=9)
    df['ema200'] = talib.EMA(df['close'], timeperiod=200)
    
    # 4. Volume SMA
    df['vol_sma'] = talib.SMA(df['volume'], timeperiod=24)
    
    # Signals
    df['oversold'] = df['rsi'] < 30 
    df['vol_spike'] = df['volume'] > (1.5 * df['vol_sma'])
    df['close_above_ema'] = df['close'] > df['ema9']
    df['uptrend'] = df['close'] > df['ema200'] # Only trade in uptrends
    
    df['crossover'] = (df['close_above_ema']) & (~df['close_above_ema'].shift(1).fillna(False))
    
    # Setup State Machine for Backtest
    trades = []
    in_position = False
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = 0.0
    entry_time = None
    highest_price = 0.0
    
    setup_active = False
    setup_expiry = 0 # Counters
    
    for current_time, row in df.iterrows():
        # 1. Manage Position
        if in_position:
            # Update Trailing Stop Logic
            if row['high'] > highest_price:
                highest_price = row['high']
            
            # If price moved 1 ATR in favor, move stop to Breakeven + small profit
            if highest_price >= entry_price + (1.0 * row['atr']):
                new_stop = max(stop_loss, entry_price + (0.1 * row['atr']))
                stop_loss = new_stop
                
            # Check Stop Loss
            if row['low'] <= stop_loss:
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
            if row['high'] >= take_profit:
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
                
            # Time Exit (10 days)
            if (current_time - entry_time).days >= 10:
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

        # 2. Check Setup (Oversold + Vol Spike + Uptrend)
        if row['oversold'] and row['vol_spike'] and row['uptrend']:
            setup_active = True
            setup_expiry = 24 
            
        if setup_active:
            setup_expiry -= 1
            if setup_expiry <= 0 or not row['uptrend']:
                setup_active = False
        
        # 3. Check Entry Trigger
        if not in_position and setup_active and row['crossover']:
            # RSI Recovery Check
            if row['rsi'] < 30:
                continue
            
            # Trend Check (Redundant but safe)
            if not row['uptrend']:
                continue
                
            entry_price = row['close']
            atr_val = row['atr']
            
            # Set Stops and Targets
            stop_loss = entry_price - (2.0 * atr_val)
            take_profit = entry_price + (6.0 * atr_val) # Reward:Risk 3:1
            
            highest_price = entry_price
            entry_time = current_time
            in_position = True
            
            setup_active = False

    # Results
    if not trades:
        print(f"--- {symbol} Results ---")
        print("No trades generated")
        return

    trades_df = pd.DataFrame(trades)
    
    total_trades = len(trades_df)
    win_rate = (trades_df['pnl'] > 0).mean()
    avg_pnl = trades_df['pnl'].mean()
    total_return = (1 + trades_df['pnl']).prod() - 1
    
    print(f"\n--- {symbol} Results ---")
    print(f"Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Total Return: {total_return:.2%}")
    print(f"Avg PnL: {avg_pnl:.2%}")
    
    return trades_df

if __name__ == "__main__":
    backtest_cascade_bounce('BTC_USDT')
    backtest_cascade_bounce('ETH_USDT')
    backtest_cascade_bounce('SOL_USDT')
