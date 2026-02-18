"""
Monte Carlo validation for Grid bot WFA trades.
"""
import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.monte_carlo.monte_carlo_validation import MonteCarloValidatorGrid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="sb")
    parser.add_argument("--symbol", default="ETH/USDT")
    parser.add_argument("--capital", type=float, default=1000)
    parser.add_argument("--investment", type=float, default=1000, help="Total investment for grid")
    parser.add_argument("--grid-lines", type=int, default=20, help="Grid lines count")
    parser.add_argument("--simulations", type=int, default=1000)
    args = parser.parse_args()

    wfa_file = f"research/walk_forward/results/wfa_grid_{args.strategy}_{args.symbol.replace('/', '_')}.csv"
    if not os.path.exists(wfa_file):
        print(f"WFA file not found: {wfa_file}")
        return

    trades = __import__("pandas").read_csv(wfa_file)
    if trades.empty or "pnl" not in trades.columns:
        print("No trades or missing pnl column.")
        return

    validator = MonteCarloValidatorGrid(
        trades,
        initial_capital=args.capital,
        investment_amount=args.investment,
        grid_lines_count=args.grid_lines,
    )
    stats, _ = validator.run_simulation(n_simulations=args.simulations)

    # Add annualized yield if exit_time available
    if "exit_time" in trades.columns:
        import pandas as pd
        exit_times = pd.to_datetime(trades["exit_time"])
        years = (exit_times.max() - exit_times.min()).total_seconds() / (365.25 * 24 * 3600)
        years = max(years, 0.001)
        median_equity = stats.get("median_final_equity", args.capital)
        total_ret = (median_equity - args.capital) / args.capital
        stats["annualized_yield_pct"] = (total_ret / years) * 100

    validator.generate_report(stats)

    os.makedirs("research/monte_carlo/results", exist_ok=True)
    out_txt = f"research/monte_carlo/results/mc_grid_{args.strategy}_{args.symbol.replace('/', '_')}.txt"
    with open(out_txt, "w") as f:
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
    print(f"Saved to {out_txt}")


if __name__ == "__main__":
    main()
