"""
Walk-Forward Analysis for Grid Bot strategies.
Usage: python run_wfa_grid.py --strategy sb --symbol ETH/USDT
"""
import sys
import os
import argparse
import pandas as pd
import numpy as np
import itertools

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from bots.grid_bot import GridBotSimulator


def _make_regime_gate_hook():
    """Return pre_test_hook that skips grid when test window regime is BULL (strong trend)."""
    def hook(train_price, test_price, best_params):
        try:
            from utils.regime_detector import CryptoRegimeDetector
            det = CryptoRegimeDetector(n_regimes=4)
            det.fit(train_price)
            regime = det.current_regime(test_price)
            if regime == "BULL":
                return False  # Skip grid in strong trend
        except Exception as e:
            print(f"    Regime gate warning: {e}, proceeding")
        return True
    return hook


def grid_strategy_sb(price_df: pd.DataFrame, funding_df=None, **params) -> pd.DataFrame:
    """S-B: Geometric grid in range."""
    if price_df is None or len(price_df) < 200:
        return pd.DataFrame()
    df = price_df.copy()
    df.columns = [c.lower() for c in df.columns]
    roll_high = df["high"].rolling(120).max().iloc[-1]
    roll_low = df["low"].rolling(120).min().iloc[-1]
    upper = roll_high
    lower = roll_low
    if upper <= lower:
        return pd.DataFrame()
    stop_bot_price = lower * 0.90  # 10% below lower — crash protection
    bot_params = {
        "upper_price": upper,
        "lower_price": lower,
        "investment_amount": params.get("investment_amount", 1000),
        "grid_lines_count": params.get("grid_lines_count", 20),
        "grid_type": "geometric",
        "trailing_up": False,
        "stop_bot_price": stop_bot_price,
        "fee": 0.001,
    }
    bot = GridBotSimulator(bot_params)
    result = bot.run(df, initial_capital=bot_params["investment_amount"])
    trades = result.get("trades_df", pd.DataFrame())
    if trades.empty:
        return pd.DataFrame()
    return trades[["pnl", "exit_time", "entry_time", "exit_reason"]].copy()


def load_data(symbol: str, days: int = 730) -> pd.DataFrame:
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    from utils.fetch_1h_data import fetch_history
    os.makedirs("data/ohlcv", exist_ok=True)
    df = fetch_history(symbol, timeframe="1h", days=days)
    df.columns = [c.lower() for c in df.columns]
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="sb", choices=["sb", "se", "sm"])
    parser.add_argument("--symbol", default="ETH/USDT")
    parser.add_argument("--train", type=int, default=365)
    parser.add_argument("--test", type=int, default=90)
    parser.add_argument("--fast", action="store_true", help="Reduced param grid for faster runs")
    parser.add_argument("--regime-gate", action="store_true",
                        help="Disable grid when regime is BULL (strong trend); uses CryptoRegimeDetector")
    args = parser.parse_args()

    strategy_map = {"sb": grid_strategy_sb}
    strategy_func = strategy_map.get(args.strategy, grid_strategy_sb)

    if args.fast:
        param_grid = {"investment_amount": [1000], "grid_lines_count": [20]}
    else:
        param_grid = {
            "investment_amount": [500, 1000],
            "grid_lines_count": [10, 15, 20, 30],
        }

    pre_test_hook = None
    if args.regime_gate:
        pre_test_hook = _make_regime_gate_hook()

    print(f"Loading {args.symbol}...")
    price_df = load_data(args.symbol)
    if price_df is None or len(price_df) < 500:
        print("Insufficient data.")
        return

    analyzer = WalkForwardAnalyzer(
        strategy_func,
        param_grid,
        price_df,
        funding_df=None,
        train_window_days=args.train,
        test_window_days=args.test,
        score_mode="sum",
        pre_test_hook=pre_test_hook,
    )
    results = analyzer.run()

    if not results.empty:
        # Grid: fixed capital per cell, don't compound. Use sum of returns.
        total_return = results["pnl"].sum()
        win_rate = (results["pnl"] > 0).mean()
        print("\n=== WFA Result (Grid) ===")
        print(f"Strategy: {args.strategy} | Symbol: {args.symbol}")
        print(f"Total Return (sum of cell returns): {total_return:.1%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        os.makedirs("research/walk_forward/results", exist_ok=True)
        out = f"research/walk_forward/results/wfa_grid_{args.strategy}_{args.symbol.replace('/', '_')}.csv"
        results.to_csv(out)
        print(f"Saved to {out}")
    else:
        print("No trades generated.")


if __name__ == "__main__":
    main()
