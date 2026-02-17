
import pandas as pd
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidator

def load_res(filepath):
    if not os.path.exists(filepath): 
        print(f"Not found: {filepath}")
        return pd.DataFrame()
    return pd.read_csv(filepath)

if __name__ == "__main__":
    symbol = "BTC_USDT" # Default for now
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
        
    wfa_file = f"research/walk_forward/results/wfa_strat1_{symbol}.csv"
    
    print(f"Loading trades from {wfa_file}...")
    trades = load_res(wfa_file)
    
    if not trades.empty:
        validator = MonteCarloValidator(trades, initial_capital=1000)
        stats, sims = validator.run_simulation(n_simulations=1000)
        validator.generate_report(stats)
        
        # Save output for report
        outfile = f"research/monte_carlo/results/mc_strat1_{symbol}.txt"
        os.makedirs(os.path.dirname(outfile), exist_ok=True)
        with open(outfile, "w") as f:
            for k, v in stats.items():
                f.write(f"{k}: {v}\n")
    else:
        print("No trades.")
