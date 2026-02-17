import sys
import os
import pandas as pd

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
    print("Running Strategy 3 V2 Backtest (Refined)")
    print("- Enabled Trend Filter (Skip Short if ADX>25 & Price>SMA200)")
    print("- Excluded 'Ecosystem' unlocks from Short logic")
    
    unlocks_df = get_upcoming_unlocks()
    unlocks_df['impact_score'] = unlocks_df.apply(score_unlock_impact, axis=1)
    
    # IMPROVEMENT: Filter out 'ecosystem' unlocks for the Short strategy
    # The research says ecosystem unlocks are bullish (+1.18%).
    # We only want to trade "High Impact Negative" events.
    
    criterion = (unlocks_df['impact_score'] < -1) & (unlocks_df['recipient_type'] != 'ecosystem')
    
    # Special case: TIA has 'investor' unlock but performed flat. APT performed bad (good for short) but failed due to trend.
    # The trend filter in UnlockTrader should handle the APT case.
    
    high_impact_unlocks = unlocks_df[criterion]
    
    print(f"Trading {len(high_impact_unlocks)} events (filtered from {len(unlocks_df)})")
    
    trader = UnlockTrader(high_impact_unlocks)
    
    tokens = ['ARB/USDT', 'OP/USDT', 'APT/USDT', 'SUI/USDT', 'TIA/USDT']
    results = {}
    
    for token in tokens:
        print(f"\nTesting {token}...")
        price_data = load_data(token)
        price_data.dropna(inplace=True) 
        
        if price_data is None or len(price_data) < 200:
            print("Insufficient data (need >200 for SMA)")
            continue
            
        # Run backtest with Trend Filter
        signals = trader.generate_signals(price_data, token, use_trend_filter=True)
        
        asset_returns = price_data['close'].pct_change()
        strategy_returns = asset_returns * signals.shift(1)
        strategy_returns = strategy_returns.dropna()
        
        if len(strategy_returns) == 0 or (signals != 0).sum() == 0:
            print("No trades generated.")
            continue
            
        # Cumulative Return
        cum_returns = (1 + strategy_returns).cumprod()
        total_return = cum_returns.iloc[-1] - 1
        sharpe = strategy_returns.mean() / strategy_returns.std() * (365**0.5) if strategy_returns.std() != 0 else 0
        max_drawdown = (cum_returns / cum_returns.cummax() - 1).min()
        
        print(f"Total Return: {total_return:.2%}")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Max Drawdown: {max_drawdown:.2%}")
        
        results[token] = {
            'return': total_return,
            'sharpe': sharpe,
            'max_dd': max_drawdown,
            'trades': (signals != 0).sum()
        }

    # Generate Report
    report_path = "research/experiments/EXP_003_v2_Refined.md"
    with open(report_path, "w") as f:
        f.write("# EXP_003_v2: Token Unlock Refined\n\n")
        f.write("## 1. Improvements\n")
        f.write("- **Trend Filter**: Added `ADX>25 & Price>SMA200` check. If Bull Trend, SKIP Short.\n")
        f.write("- **Selection**: Excluded `ecosystem` unlocks (historically bullish).\n\n")
        f.write("## 2. Results\n\n")
        
        f.write("| Token | Return | Sharpe | Max DD | Trades |\n")
        f.write("|-------|--------|--------|--------|--------|\n")
        for token, res in results.items():
            f.write(f"| {token} | {res['return']:.2%} | {res['sharpe']:.2f} | {res['max_dd']:.2%} | {res['trades']} |\n")
            
    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    run()
