
import pandas as pd
import numpy as np
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from utils.data_loader import load_ohlcv

def strategy_logic_1(price_df, funding_df=None, ma_fast=50, ma_slow=200, stop_loss=0.03):
    """
    Strategy 1: Weekend Momentum with Trend Filter
    Entries: Friday Close AND (MA_Fast > MA_Slow)
    Exits: Monday Close OR Stop Loss
    """
    if price_df.empty:
        return None
        
    df = price_df.copy()
    close = df['close']
    
    # Calculate Indicators
    # We need enough data for the slow MA
    if len(close) < ma_slow + 10:
        return None

    # Using pandas rolling for MAs (simple and fast enough for WFA loop, or use talib if desired)
    # df['ma_fast'] = talib.EMA(close.values, timeperiod=ma_fast) # If talib available
    df['ma_fast'] = close.rolling(window=ma_fast).mean()
    df['ma_slow'] = close.rolling(window=ma_slow).mean()
    
    # Identify Fridays and Mondays
    # dayofweek: 0=Mon, 4=Fri
    is_friday = df.index.dayofweek == 4
    is_monday = df.index.dayofweek == 0
    
    trades = []
    position = None 
    
    # Loop
    # Start after slow MA valid
    start_idx = ma_slow
    
    for i in range(start_idx, len(df)-1):
        curr_date = df.index[i]
        curr_close = close.iloc[i]
        
        # Check Exit first (Monday or SL)
        if position:
            pnl_pct = (curr_close - position['entry_price']) / position['entry_price']
            should_exit = False
            exit_reason = ''
            
            # SL Check
            if pnl_pct < -stop_loss:
                should_exit = True
                exit_reason = 'Stop Loss'
            # Time Exit (Monday)
            elif curr_date.dayofweek == 0: # Monday
                should_exit = True
                exit_reason = 'Monday Exit'
                
            if should_exit:
                trades.append({
                    'exit_time': curr_date,
                    'pnl': pnl_pct,
                    'exit_reason': exit_reason
                })
                position = None
        
        # Check Entry (Friday + Trend)
        if position is None:
            if curr_date.dayofweek == 4: # Friday
                ma_f = df['ma_fast'].iloc[i]
                ma_s = df['ma_slow'].iloc[i]
                
                if ma_f > ma_s: # Bullish Trend
                    position = {
                        'side': 'long',
                        'entry_price': curr_close,
                        'entry_time': curr_date
                    }

    return pd.DataFrame(trades)

def load_data_daily(symbol):
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1d.csv"
    try:
        return load_ohlcv(path)
    except FileNotFoundError:
        print(f"Data not found: {path}")
        return None

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='BTC/USDT')
    args = parser.parse_args()

    print(f"Loading daily data for {args.symbol}...")
    price = load_data_daily(args.symbol)
    
    if price is None:
        sys.exit(1)
        
    # Param Grid for Optimization
    param_grid = {
        'ma_fast': [10, 20, 50],
        'ma_slow': [50, 100, 200],
        'stop_loss': [0.03, 0.05, 0.10]
    }
    
    # Filter combinations where fast >= slow to save time (conceptually invalid)
    # The Analyzer does cartesian product. We can handle invalid combos in strategy or just let them run (fast=50, slow=50 is valid but useless).
    # We'll just run all.
    
    analyzer = WalkForwardAnalyzer(
        strategy_logic_1,
        param_grid,
        price,
        funding_df=None, # Not used
        train_window_days=365, # 1 year train (needs to capture trend regimes)
        test_window_days=90    # 3 months test
    )
    
    results = analyzer.run()
    
    if not results.empty:
        total_return = (results['pnl'] + 1).prod() - 1
        win_rate = (results['pnl'] > 0).mean()
        
        print("\n=== Walk-Forward Result (Strategy 1) ===")
        print(f"Total Return: {total_return:.2%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        
        # Save results
        os.makedirs("research/walk_forward/results", exist_ok=True)
        filename = f"research/walk_forward/results/wfa_strat1_{args.symbol.replace('/','_')}.csv"
        results.to_csv(filename)
        print(f"Saved trades to {filename}")
    else:
        print("No trades generated in WFA.")
