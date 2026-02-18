"""
Monte Carlo validation for Strategy 8: Whale Accumulation Tracker
Resamples OOS trades from WFA; reports ruin prob, prob DD>20%, median equity.
Run: python research/monte_carlo/run_mc_strategy_8.py
      python research/monte_carlo/run_mc_strategy_8.py --pooled
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidator
import pandas as pd


def load_wfa_results(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return pd.DataFrame()
    return pd.read_csv(filepath)


if __name__ == "__main__":
    import argparse
    import pandas as pd

    parser = argparse.ArgumentParser()
    parser.add_argument('--pooled', action='store_true', help='Use pooled WFA results')
    args = parser.parse_args()

    if args.pooled:
        wfa_file = "research/walk_forward/results/wfa_strat8_pooled.csv"
    else:
        wfa_file = "research/walk_forward/results/wfa_strat8_ETH_USDT.csv"

    print(f"Loading trades from {wfa_file}...")
    trades = load_wfa_results(wfa_file)

    if trades.empty:
        print("No WFA trades found. Run: python research/walk_forward/run_wfa_strategy_8.py [--pool]")
        sys.exit(1)

    if 'pnl' not in trades.columns:
        print("Trades must have 'pnl' column.")
        sys.exit(1)

    validator = MonteCarloValidator(trades, initial_capital=1000)
    stats, _ = validator.run_simulation(n_simulations=1000)
    validator.generate_report(stats)

    os.makedirs("research/monte_carlo/results", exist_ok=True)
    out_file = "research/monte_carlo/results/mc_strat8_pooled.txt" if args.pooled else "research/monte_carlo/results/mc_strat8_eth.txt"
    with open(out_file, "w") as f:
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
    print(f"Saved to {out_file}")
