
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from datetime import datetime

def load_data(symbol, timeframe='1h'):
    """Load OHLCV and Funding Rate data"""
    # Load OHLCV
    ohlcv_path = f"data/ohlcv/{symbol.replace('/', '_')}_{timeframe}.csv"
    if not os.path.exists(ohlcv_path):
        print(f"❌ OHLCV data not found: {ohlcv_path}")
        return None, None
    
    price_df = pd.read_csv(ohlcv_path, parse_dates=['datetime'], index_col='datetime')
    
    # Load Funding
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
                                     z_score_threshold=2.0,
                                     adx_threshold=25,
                                     stop_loss=0.05):
    """
    Backtest Funding Rate Mean Reversion (1h)
    """
    price_df, funding_df = load_data(symbol, timeframe='1h')
    if funding_df is None:
        return
        
    print(f"\n--- Backtesting {symbol} (1h) ---")
    print(f"Data range: {price_df.index.min()} to {price_df.index.max()}")
    
    # Merge and align
    df = price_df.copy()
    
    # Resample funding to hourly (ffill)
    funding_hourly = funding_df['fundingRate'].resample('1h').ffill()
    
    # Join
    df = df.join(funding_hourly)
    df['fundingRate'] = df['fundingRate'].fillna(method='ffill')
    
    # Calculate Indicators
    # 1. Z-Score
    df['funding_mean'] = df['fundingRate'].rolling(window=24).mean()
    df['funding_std'] = df['fundingRate'].rolling(window=24).std()
    df['funding_zscore'] = (df['fundingRate'] - df['funding_mean']) / df['funding_std']
    
    # 2. ADX (using pandas-ta or talib if available, simple fallback if not)
    # Just use High-Low match for now or try talib
    try:
        import talib
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    except:
        print("TALib not found, skipping ADX filter (all allowed)")
        df['adx'] = 0 
    
    trades = []
    position = None 
    
    for i in range(24, len(df)-1):
        curr_time = df.index[i]
        curr_close = df['close'].iloc[i]
        z_score = df['funding_zscore'].iloc[i]
        adx = df['adx'].iloc[i]
        
        # Check Exit
        if position:
            pnl_pct = 0
            should_exit = False
            exit_reason = ''
            
            if position['side'] == 'long':
                pnl_pct = (curr_close - position['entry_price']) / position['entry_price']
                # Exit if Z-Score crosses 0 (strict mean reversion)
                if z_score > 0: 
                    should_exit = True
                    exit_reason = 'Mean Reverted'
                elif pnl_pct < -stop_loss:
                    should_exit = True
                    exit_reason = 'Stop Loss'
                    
            else: # short
                pnl_pct = (position['entry_price'] - curr_close) / position['entry_price']
                # Exit if Z-Score crosses 0
                if z_score < 0:
                    should_exit = True
                    exit_reason = 'Mean Reverted'
                elif pnl_pct < -stop_loss:
                    should_exit = True
                    exit_reason = 'Stop Loss'
            
            if should_exit:
                trades.append({
                    'entry_time': position['entry_time'],
                    'exit_time': curr_time,
                    'side': position['side'],
                    'entry_price': position['entry_price'],
                    'exit_price': curr_close,
                    'pnl': pnl_pct,
                    'exit_reason': exit_reason
                })
                position = None
                
        # Check Entry
        if position is None:
            # Filter: non-trending market
            if adx < adx_threshold:
                # Long: Z < -2
                if z_score < -z_score_threshold:
                    position = {
                        'side': 'long',
                        'entry_price': curr_close,
                        'entry_time': curr_time
                    }
                # Short: Z > 2
                elif z_score > z_score_threshold:
                    position = {
                        'side': 'short',
                        'entry_price': curr_close,
                        'entry_time': curr_time
                    }

    # Analyze results
    if not trades:
        print("No trades generated.")
        return

    results = pd.DataFrame(trades)
    
    win_rate = len(results[results['pnl'] > 0]) / len(results)
    avg_pnl = results['pnl'].mean()
    total_return = (results['pnl'] + 1).prod() - 1
    
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
