import sys
import os
import pandas as pd
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.getcwd())

from strategies.UnlockTrader import UnlockTrader
from utils.unlock_data_loader import get_upcoming_unlocks, score_unlock_impact

def load_data(symbol):
    filename = f"data/ohlcv/{symbol.replace('/', '_')}_1d.csv"
    if not os.path.exists(filename):
        print(f"Data not found for {symbol}")
        return None
    df = pd.read_csv(filename)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    return df

def run():
    print("Running Strategy 3 Backtest: Token Unlocks")
    
    unlocks_df = get_upcoming_unlocks()
    # Filter for high impact only?
    unlocks_df['impact_score'] = unlocks_df.apply(score_unlock_impact, axis=1)
    
    # Filter negative impact events
    high_impact_unlocks = unlocks_df[unlocks_df['impact_score'] < -1]
    
    trader = UnlockTrader(high_impact_unlocks)
    
    tokens = ['ARB/USDT', 'OP/USDT', 'APT/USDT', 'SUI/USDT', 'TIA/USDT']
    results = {}
    
    for token in tokens:
        print(f"\nTesting {token}...")
        price_data = load_data(token)
        if price_data is None:
            continue
            
        returns = trader.run_backtest(price_data, token)
        
        if len(returns) == 0:
            print("No trades generated.")
            continue
            
        # Cumulative Return
        cum_returns = (1 + returns).cumprod()
        total_return = cum_returns.iloc[-1] - 1
        sharpe = returns.mean() / returns.std() * (365**0.5) if returns.std() != 0 else 0
        max_drawdown = (cum_returns / cum_returns.cummax() - 1).min()
        
        print(f"Total Return: {total_return:.2%}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Max Drawdown: {max_drawdown:.2%}")
        
        results[token] = {
            'return': total_return,
            'sharpe': sharpe,
            'max_dd': max_drawdown,
            'equity_curve': cum_returns
        }

    # Generate Report
    report_path = "research/experiments/EXP_003_TokenUnlocks.md"
    with open(report_path, "w") as f:
        f.write("# EXP_003: Token Unlock Event Trading\n\n")
        f.write("## 1. Hypothesis\n")
        f.write("**Hypothesis:** Assets with large token unlocks (>2% supply) experience negative price pressure 30 days prior and stabilize 14 days post-unlock.\n\n")
        f.write("## 2. Methodology\n")
        f.write("- **Strategy**: Short 30 days before, Long 14 days after.\n")
        f.write("- **Assets**: ARB, OP, APT, SUI, TIA.\n\n")
        f.write("## 3. Results\n\n")
        
        f.write("| Token | Return | Sharpe | Max DD |\n")
        f.write("|-------|--------|--------|--------|\n")
        for token, res in results.items():
            f.write(f"| {token} | {res['return']:.2%} | {res['sharpe']:.2f} | {res['max_dd']:.2%} |\n")
            
    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    run()
