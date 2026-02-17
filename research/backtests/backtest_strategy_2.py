
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

def load_data(symbol, timeframe='1d'):
    """Load OHLCV and Funding Rate data"""
    # Load OHLCV
    ohlcv_path = f"data/ohlcv/{symbol.replace('/', '_')}_{timeframe}.csv"
    if not os.path.exists(ohlcv_path):
        print(f"❌ OHLCV data not found: {ohlcv_path}")
        return None, None
    
    price_df = pd.read_csv(ohlcv_path, parse_dates=['datetime'], index_col='datetime')
    
    # Load Funding
    # Handle different symbol formats if needed (e.g. BTC/USDT vs BTC/USDT:USDT)
    # The collector saves as safe_symbol which replaces / and : with _
    # ex: BTC/USDT:USDT -> BTC_USDT_USDT
    base_symbol = symbol.replace('/', '_')
    funding_path = f"data/funding_rates/{base_symbol}_USDT_funding.csv"
    
    if not os.path.exists(funding_path):
         funding_path = f"data/funding_rates/{base_symbol}_funding.csv"
    
    if not os.path.exists(funding_path):
        print(f"❌ Funding data not found: {funding_path}")
        return price_df, None
        
    funding_df = pd.read_csv(funding_path, parse_dates=['datetime'], index_col='datetime')
    
    return price_df, funding_df

def backtest_funding_mean_reversion(symbol, 
                                     entry_threshold=0.0005, # 0.05%
                                     exit_threshold=0.0001,  # 0.01%
                                     stop_loss=0.02):        # 2%
    """
    Backtest Funding Rate Mean Reversion
    Entry: Funding > threshold (Short) or Funding < -threshold (Long)
    Exit: Funding < exit_threshold (abs) or Stop Loss
    """
    price_df, funding_df = load_data(symbol)
    if funding_df is None:
        return
        
    print(f"\n--- Backtesting {symbol} ---")
    print(f"Data range: {price_df.index.min()} to {price_df.index.max()}")
    
    # Resample funding to match price timeframe (1d)
    # We take the mean funding rate of the day, or the last one? 
    # Usually funding is every 8h. The 'sentiment' is best captured by the average or the extreme of the day.
    # Let's use the mean for the day to smooth it, or look for ANY breach in the day (max/min).
    # For a daily strategy, let's use the last closed funding rate of the previous day to enter at Open, or 
    # if we assume we trade at Close, we use the funding rate OF that day.
    # Let's simplisticly reindex to daily, ffilling.
    
    # Align data
    df = price_df.copy()
    # Funding data might have duplicates or multiple entries per day
    # calculated weighted average or just mean? Mean is fine.
    funding_daily = funding_df['fundingRate'].resample('1D').mean()
    
    df['fundingRate'] = funding_daily
    df['fundingRate'] = df['fundingRate'].fillna(method='ffill')
    
    trades = []
    position = None # {'side': 'long'|'short', 'price': 123, 'time': dt}
    
    for i in range(1, len(df)-1):
        # We look at data available at index i to decide trade at i (Close) or i+1 (Open).
        # VectorBT/Freqtrade usually trade at Close of candle i or Open of i+1.
        # Let's assume we trade at CLOSE of day i if signal exists.
        
        curr_date = df.index[i]
        curr_close = df['close'].iloc[i]
        curr_funding = df['fundingRate'].iloc[i]
        
        # Check Exit first
        if position:
            pnl = 0
            exit_reason = ''
            
            # Check Stop Loss
            if position['side'] == 'long':
                pnl_pct = (curr_close - position['entry_price']) / position['entry_price']
            else:
                pnl_pct = (position['entry_price'] - curr_close) / position['entry_price']
                
            if pnl_pct < -stop_loss:
                exit_reason = 'Stop Loss'
                should_exit = True
            elif abs(curr_funding) < exit_threshold:
                 exit_reason = 'Funding Normal'
                 should_exit = True
            else:
                should_exit = False
                
            if should_exit:
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': curr_date,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': curr_close,
                    'pnl': pnl_pct,
                    'exit_reason': exit_reason,
                    'entry_funding': position['entry_funding'],
                    'exit_funding': curr_funding
                })
                position = None
                
        # Check Entry
        if position is None:
            # Signal: Extreme Negative Funding -> LONG
            if curr_funding < -entry_threshold:
                position = {
                    'side': 'long',
                    'entry_price': curr_close,
                    'entry_time': curr_date,
                    'entry_funding': curr_funding
                }
            # Signal: Extreme Positive Funding -> SHORT
            elif curr_funding > entry_threshold:
                position = {
                    'side': 'short',
                    'entry_price': curr_close,
                    'entry_time': curr_date,
                    'entry_funding': curr_funding
                }

    # Analyze results
    if not trades:
        print("No trades generated.")
        return

    results = pd.DataFrame(trades)
    
    win_rate = len(results[results['pnl'] > 0]) / len(results)
    avg_pnl = results['pnl'].mean()
    total_return = (results['pnl'] + 1).prod() - 1
    
    # Calculate Max Drawdown
    results['cum_ret'] = (results['pnl'] + 1).cumprod()
    results['cum_max'] = results['cum_ret'].cummax()
    results['drawdown'] = (results['cum_ret'] - results['cum_max']) / results['cum_max']
    max_dd = results['drawdown'].min()
    
    print(f"Trades: {len(results)}")
    print(f"Win Rate: {win_rate:.2%}")
    print(f"Avg PnL: {avg_pnl:.2%}")
    print(f"Total Return: {total_return:.2%}")
    print(f"Max Drawdown: {max_dd:.2%}")
    
    return results

if __name__ == "__main__":
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    for sym in symbols:
        backtest_funding_mean_reversion(sym)
