import pandas as pd
import numpy as np
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from research.backtests.backtest_strategy_1_v2 import WeekendMomentumBacktester, fetch_data
# We'll need to slightly modify backtesters to return equity curves reliably or reconstruct them.
# For simplicity, we'll re-run a simplified version of each here.

def get_strat1_equity(symbol='BTC/USDT'):
    df = fetch_data(symbol, '1d', limit=1000)
    tester = WeekendMomentumBacktester(use_regime_filter=True)
    df = tester.prepare_data(df)
    
    # Simple loop reproduction to get time-series
    capital = 1000.0
    position = 0
    entry_price = 0
    equity_curve = pd.Series(index=df.index, data=1000.0)
    
    for i in range(200, len(df)):
        curr_row = df.iloc[i]
        date = df.index[i]
        price = curr_row['close']
        
        if position > 0:
            pnl = (price - entry_price) / entry_price
            if price <= entry_price * 0.97 or curr_row['day_of_week'] == 0:
                capital *= (1 + pnl) * 0.999 # Exit fee
                position = 0
        elif curr_row['day_of_week'] == 4: # Friday
            if curr_row['ema50'] > curr_row['ema200'] and curr_row.get('regime') != 'BEAR':
                capital *= 0.999 # Entry fee
                position = capital / price
                entry_price = price
        
        equity_curve.loc[date] = capital if position == 0 else position * price
    return equity_curve

def analyze():
    print("--- Correlation Analysis: Strategies 1, 2, 3 ---")
    
    files = {
        'Strat1_BTC': 'research/backtests/equity_strat1_BTC_USDT.csv',
        'Strat2_BTC': 'research/backtests/equity_strat2_BTC_USDT.csv',
        'Strat3_ARB': 'research/backtests/equity_strat3_ARB_USDT.csv'
    }
    
    dataframes = []
    for name, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path, index_col=0, parse_dates=True)
            df.columns = ['equity']
            # Calculate daily returns
            returns = df['equity'].pct_change().fillna(0)
            returns.name = name
            dataframes.append(returns)
        else:
            print(f"Warning: {path} not found.")


    if not dataframes:
        print("No data available for correlation.")
        return

    # Merge all
    merged = pd.concat(dataframes, axis=1).dropna()
    
    print(f"\nAligned Data: {len(merged)} days")
    
    # Correlation Matrix
    corr_matrix = merged.corr()
    print("\nPearson Correlation Matrix:")
    print(corr_matrix)
    
    # Combined Portfolio
    # Assume equal weight (rough proxy)
    merged['Portfolio'] = merged.mean(axis=1)
    cum_portfolio = (1 + merged['Portfolio']).cumprod()
    
    total_ret = cum_portfolio.iloc[-1] - 1
    max_dd = (cum_portfolio / cum_portfolio.cummax() - 1).min()
    sharpe = merged['Portfolio'].mean() / merged['Portfolio'].std() * np.sqrt(365)
    
    print("\n--- Combined Portfolio Stats (Equal Weight) ---")
    print(f"Total Return: {total_ret:.2%}")
    print(f"Max Drawdown: {max_dd:.2%}")
    print(f"Portfolio Sharpe: {sharpe:.2f}")

if __name__ == "__main__":
    analyze()

