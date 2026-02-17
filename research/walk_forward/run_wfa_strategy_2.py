
import pandas as pd
import numpy as np
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from utils.data_loader import find_funding_path

# Re-implement strategy logic function that accepts dataframes directly
# (Importing from backtest_strategy_2 might be messy if it relies on loading files internally)

def strategy_logic(price_df, funding_df, z_score_threshold=2.0, adx_threshold=25, stop_loss=0.05):
    # Data is already sliced by Analyzer
    if price_df.empty or funding_df is None or funding_df.empty:
        return None
        
    df = price_df.copy()
    
    # Resample funding
    funding_hourly = funding_df['fundingRate'].resample('1h').ffill()
    
    # Align indices (intersection)
    # Reindex funding to match price info
    funding_hourly = funding_hourly.reindex(df.index, method='ffill')
    df['fundingRate'] = funding_hourly
    df['fundingRate'] = df['fundingRate'].ffill() # pandas 2.0+ use ffill()
    
    # Indicators
    # Need sufficient data for rolling windows (24h)
    if len(df) < 50: 
        return None
        
    df['funding_mean'] = df['fundingRate'].rolling(window=24).mean()
    df['funding_std'] = df['fundingRate'].rolling(window=24).std()
    
    # Handle std=0
    df['funding_zscore'] = 0.0
    mask_std = df['funding_std'] != 0
    df.loc[mask_std, 'funding_zscore'] = (df.loc[mask_std, 'fundingRate'] - df.loc[mask_std, 'funding_mean']) / df.loc[mask_std, 'funding_std']
    
    # ADX
    try:
        import talib
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
    except:
        df['adx'] = 0
        
    trades = []
    position = None
    
    # Iteration (Vectorized would be faster for WFA but loop is safer for logic preservation)
    # Skip warm-up period
    warmup = 30
    
    for i in range(warmup, len(df)-1):
        curr_time = df.index[i]
        curr_close = df['close'].iloc[i]
        z_score = df['funding_zscore'].iloc[i]
        adx = df['adx'].iloc[i]
        
        if position:
            pnl_pct = 0
            should_exit = False
            
            if position['side'] == 'long':
                pnl_pct = (curr_close - position['entry_price']) / position['entry_price']
                if z_score > 0 or pnl_pct < -stop_loss:
                    should_exit = True
            else:
                pnl_pct = (position['entry_price'] - curr_close) / position['entry_price']
                if z_score < 0 or pnl_pct < -stop_loss:
                    should_exit = True
                    
            if should_exit:
                trades.append({
                    'exit_time': curr_time,
                    'pnl': pnl_pct
                })
                position = None
        
        if position is None:
            if adx < adx_threshold:
                if z_score < -z_score_threshold:
                    position = {'side': 'long', 'entry_price': curr_close}
                elif z_score > z_score_threshold:
                    position = {'side': 'short', 'entry_price': curr_close}
                    
    return pd.DataFrame(trades)

def load_full_data(symbol):
    ohlcv_path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    funding_path = find_funding_path(symbol)
    if not funding_path:
        raise FileNotFoundError(f"Funding data not found for {symbol}. Run: python utils/fetch_1h_data.py")

    price_df = pd.read_csv(ohlcv_path, parse_dates=['datetime'], index_col='datetime')
    funding_df = pd.read_csv(funding_path, parse_dates=['datetime'], index_col='datetime')
    if 'fundingRate' not in funding_df.columns and 'funding_rate' in funding_df.columns:
        funding_df = funding_df.rename(columns={'funding_rate': 'fundingRate'})
    return price_df, funding_df

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='ETH/USDT')
    args = parser.parse_args()
    
    print(f"Loading data for {args.symbol}...")
    try:
        price, funding = load_full_data(args.symbol)
    except FileNotFoundError:
        print("Data not found. Run data_collector.py and convert to 1h first if needed.")
        sys.exit(1)
        
    param_grid = {
        'z_score_threshold': [1.5, 2.0, 2.5, 3.0],
        'adx_threshold': [20, 25, 30],
        'stop_loss': [0.03, 0.05, 0.07]
    }
    
    analyzer = WalkForwardAnalyzer(
        strategy_logic, 
        param_grid, 
        price, 
        funding,
        train_window_days=180, # 6 months train
        test_window_days=30    # 1 month test
    )
    
    results = analyzer.run()
    
    if not results.empty:
        total_return = (results['pnl'] + 1).prod() - 1
        win_rate = (results['pnl'] > 0).mean()
        
        print("\n=== Walk-Forward Result ===")
        print(f"Total Return: {total_return:.2%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        
        # Save results
        os.makedirs("research/walk_forward/results", exist_ok=True)
        filename = f"research/walk_forward/results/wfa_{args.symbol.replace('/','_')}.csv"
        results.to_csv(filename)
        print(f"Saved trades to {filename}")
    else:
        print("No trades generated in WFA.")
