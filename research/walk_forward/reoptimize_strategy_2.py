"""
Periodic re-optimization for Strategy 2 (Funding Reversion on ETH).

Strategy 2's edge is parameter-sensitive and time-varying: the v2 backtest shows
-14.98% with fixed params while WFA shows +44.64% with per-window optimization.
This script re-fits parameters monthly using the most recent 180 days, exactly
as the WFA does. Run it monthly (e.g., via cron) and use the output params for
paper trading until the next re-optimization.

Usage:
  python research/walk_forward/reoptimize_strategy_2.py --symbol ETH/USDT
  python research/walk_forward/reoptimize_strategy_2.py --symbol ETH/USDT --output params.json
"""
import sys
import os
import json
import argparse
from datetime import timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.walk_forward.run_wfa_strategy_2 import strategy_logic, load_full_data
from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer


def reoptimize(symbol='ETH/USDT', train_days=180, output_path=None):
    """
    Re-fit Strategy 2 parameters using the most recent train_days of data.
    Returns best params for paper trading.
    """
    print(f"Loading data for {symbol}...")
    price, funding = load_full_data(symbol)

    # Use last train_days; optimize() uses exclusive end, so add 1 day to include latest
    end_date = price.index.max() + timedelta(days=1)
    start_date = end_date - timedelta(days=train_days)

    print(f"Training window: {start_date.date()} -> {price.index.max().date()} ({train_days} days)")

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
        train_window_days=train_days,
        test_window_days=30
    )

    best_params, best_score = analyzer.optimize(start_date, end_date)

    if best_params is None:
        print("No profitable params found in training window.")
        return None

    print(f"\n=== Re-optimization Result ===")
    print(f"Best params: {best_params}")
    print(f"Training score (return): {best_score:.2%}")

    result = {
        'symbol': symbol,
        'train_end': str(end_date.date()),
        'train_days': train_days,
        'params': best_params,
        'train_score': best_score
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved params to {output_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Re-optimize Strategy 2 params for paper trading (run monthly)"
    )
    parser.add_argument('--symbol', default='ETH/USDT', help='Symbol (Strategy 2: ETH only)')
    parser.add_argument('--train-days', type=int, default=180, help='Training window (default: 180)')
    parser.add_argument('--output', '-o', help='Output JSON path for params')
    args = parser.parse_args()

    try:
        reoptimize(args.symbol, args.train_days, args.output)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Run: python utils/fetch_1h_data.py to fetch 1h OHLCV and funding data first.")
        sys.exit(1)
