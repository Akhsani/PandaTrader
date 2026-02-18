"""
Monte Carlo validation for Signal bot WFA trades.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="sd")
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--capital", type=float, default=1000)
    parser.add_argument("--simulations", type=int, default=1000)
    args = parser.parse_args()

    wfa_file = f"research/walk_forward/results/wfa_signal_{args.strategy}_{args.symbol.replace('/', '_')}.csv"
    if not os.path.exists(wfa_file):
        print(f"WFA file not found: {wfa_file}")
        return

    trades = __import__("pandas").read_csv(wfa_file)
    if trades.empty or "pnl" not in trades.columns:
        print("No trades or missing pnl column.")
        return

    validator = MonteCarloValidator(trades, initial_capital=args.capital)
    stats, _ = validator.run_simulation(n_simulations=args.simulations)
    validator.generate_report(stats)

    os.makedirs("research/monte_carlo/results", exist_ok=True)
    out_txt = f"research/monte_carlo/results/mc_signal_{args.strategy}_{args.symbol.replace('/', '_')}.txt"
    with open(out_txt, "w") as f:
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
    print(f"Saved to {out_txt}")


if __name__ == "__main__":
    main()
