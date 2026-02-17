import sys
import os
import pandas as pd
import numpy as np
import talib

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
    print("Running Strategy 3 V3 Optimization (Funding Costs + Graduated Sizing)")
    
    unlocks_df = get_upcoming_unlocks()
    unlocks_df['impact_score'] = unlocks_df.apply(score_unlock_impact, axis=1)
    
    # Filter: High Impact Negative AND Not Ecosystem
    criterion = (unlocks_df['impact_score'] < -1) & (unlocks_df['recipient_type'] != 'ecosystem')
    high_impact_unlocks = unlocks_df[criterion]
    
    trader = UnlockTrader(high_impact_unlocks)
    
    tokens = ['ARB/USDT', 'OP/USDT', 'APT/USDT', 'SUI/USDT', 'TIA/USDT']
    results = {}
    
    for token in tokens:
        print(f"\nTesting {token}...")
        price_data = load_data(token)
        price_data.dropna(inplace=True) 
        
        if price_data is None or len(price_data) < 200:
            continue
            
        # 1. Generate Signals & Multipliers
        # generate_signals now returns DataFrame with ['signal', 'size_multiplier']
        signals_df = trader.generate_signals(price_data, token, use_trend_filter=True)
        
        signals = signals_df['signal']
        multipliers = signals_df['size_multiplier']
        
        # 2. Calculate BASELINE Returns (Size=1.0 always, No Funding Cost)
        # We manually force multiplier to 1.0 for baseline comparison
        asset_returns = price_data['close'].pct_change()
        baseline_returns = asset_returns * signals.shift(1)
        
        # 3. Calculate OPTIMIZED Returns (Size=1.5x in Bull, Funding Cost Applied)
        # Funding Cost: If Short (-1) AND Bull Trend -> Subtract 0.0003 (0.03%) per day
        # We need to reconstruct Short + Bull Trend status
        
        close = price_data['close'].values
        adx = talib.ADX(price_data['high'], price_data['low'], close, timeperiod=14)
        sma200 = talib.SMA(close, timeperiod=200)
        is_bull = (adx > 25) & (close > sma200)
        is_bull_series = pd.Series(is_bull, index=price_data.index).fillna(False)
        
        # Apply Logic
        opt_returns_list = []
        
        # Loop mainly to handle Funding Cost conditional logic correctly on a daily basis
        # Vectorized is faster but loop is clearer for this specific cost logic
        
        # Shift signals/multipliers for trade execution
        exec_signals = signals.shift(1).fillna(0)
        exec_sizes = multipliers.shift(1).fillna(1.0)
        
        funding_cost_daily = 0.0003 # 0.03%
        
        # Vectorized Optimized Calculation
        # Raw PnL = returns * signal * size
        raw_pnl = asset_returns * exec_signals * exec_sizes
        
        # Apply Transaction Costs (0.10% per side = 0.20% round trip)
        # Entry cost when signal starts being non-zero
        # Exit cost when signal returns to zero
        # Shifted comparison for cost detection
        trades = exec_signals.diff().abs().fillna(0)
        transaction_costs = trades * 0.0010
        
        # Apply Funding Cost Penalties (Already in v3 plan)
        is_short = (exec_signals == -1)
        funding_penalty = pd.Series(0.0, index=raw_pnl.index)
        funding_penalty[is_short] = funding_cost_daily 
        
        opt_returns = raw_pnl - funding_penalty - transaction_costs
        baseline_net_returns = (asset_returns * exec_signals) - transaction_costs
        
        # Clean up
        baseline_returns = baseline_net_returns.dropna()
        opt_returns = opt_returns.dropna()

        
        # Stats
        def calc_stats(rets):
            cum = (1 + rets).cumprod()
            tot = cum.iloc[-1] - 1
            dd = (cum / cum.cummax() - 1).min()
            return tot, dd

        base_tot, base_dd = calc_stats(baseline_returns)
        opt_tot, opt_dd = calc_stats(opt_returns)
        
        print(f"  Baseline:  Return={base_tot:.2%} | MaxDD={base_dd:.2%}")
        print(f"  Optimized: Return={opt_tot:.2%} | MaxDD={opt_dd:.2%}")
        
        results[token] = {
            'base_ret': base_tot,
            'opt_ret': opt_tot,
            'improvement': opt_tot - base_tot
        }

        # Save equity curve for correlation analysis
        (1 + opt_returns).cumprod().to_csv(f"research/backtests/equity_strat3_{token.replace('/', '_')}.csv")
        
    # Summary
    print("\n--- SUMMARY ---")
    avg_imp = np.mean([r['improvement'] for r in results.values()]) if results else 0
    print(f"Average Return Improvement: {avg_imp:.2%} points")
    
    if avg_imp > 0:
        print("SUCCESS: Graduated Sizing overcame Funding Costs.")
    else:
        print("FAIL: Optimizations did not improve returns.")

if __name__ == "__main__":
    run()
