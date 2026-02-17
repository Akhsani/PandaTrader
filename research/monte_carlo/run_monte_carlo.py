
import pandas as pd
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidator

def load_wfa_results(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File not found {filepath}")
        return pd.DataFrame()
    return pd.read_csv(filepath)

if __name__ == "__main__":
    # Load ETH WFA results
    wfa_file = "research/walk_forward/results/wfa_ETH_USDT.csv"
    
    print(f"Loading trades from {wfa_file}...")
    trades = load_wfa_results(wfa_file)
    
    if not trades.empty:
        validator = MonteCarloValidator(trades, initial_capital=1000)
        stats, sims = validator.run_simulation(n_simulations=1000)
        validator.generate_report(stats)
        
        # Save stats
        os.makedirs("research/monte_carlo/results", exist_ok=True)
        with open("research/monte_carlo/results/mc_eth_usdt.txt", "w") as f:
            for k, v in stats.items():
                f.write(f"{k}: {v}\n")
    else:
        print("No trades found to validate.")
