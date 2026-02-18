"""
Grid search optimization for DCA bot parameters.
"""
import sys
import os
import argparse
from itertools import product
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.dca_bot import DCABotSimulator

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_rsi(close, period=7):
    if HAS_TALIB:
        return talib.RSI(close, timeperiod=period).fillna(50)
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def load_data(symbol):
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    else:
        from utils.fetch_1h_data import fetch_history
        os.makedirs("data/ohlcv", exist_ok=True)
        df = fetch_history(symbol, timeframe="1h", days=730)
    df.columns = [c.lower() for c in df.columns]
    return df


PARAM_GRID = {
    "base_order_volume": [20, 25, 30],
    "safety_order_volume": [25, 30, 40],
    "max_safety_orders": [3, 4, 5],
    "safety_order_step_percentage": [0.5, 0.75, 1.0, 1.5],
    "martingale_volume_coefficient": [1.5, 2.0, 2.25, 2.5],
    "martingale_step_coefficient": [1.0, 1.5, 2.0],
    "take_profit_percentage": [1.5, 2.0, 2.5, 3.0],
    "trailing_take_profit": [True, False],
    "trailing_take_profit_deviation": [0.3, 0.5],
    "fee": [0.001],
}


def grid_search_dca(ohlcv, signal_series, param_grid=None):
    param_grid = param_grid or PARAM_GRID
    keys = list(param_grid.keys())
    results = []
    for combo in product(*param_grid.values()):
        params = dict(zip(keys, combo))
        bot = DCABotSimulator(params)
        metrics = bot.run(ohlcv, signal_series, initial_capital=10000)
        results.append({**params, **{k: metrics.get(k, v) for k, v in [
            ("sharpe_ratio", 0), ("max_drawdown", 0), ("win_rate", 0),
            ("total_deals", 0), ("total_profit_pct", 0),
        ]}})
    df = pd.DataFrame(results)
    df = df.sort_values("sharpe_ratio", ascending=False)
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    print(f"Loading {args.symbol}...")
    df = load_data(args.symbol)
    if df is None or len(df) < 100:
        print("Insufficient data.")
        return

    df["rsi"] = compute_rsi(df["close"], 7)
    s = (df["rsi"] < 20).shift(1)
    signal = s.where(s.notna(), False).astype(bool)

    print("Running grid search...")
    results = grid_search_dca(df, signal)
    top = results.head(args.top)
    print(f"\nTop {args.top} by Sharpe:")
    print(top[["base_order_volume", "safety_order_volume", "max_safety_orders",
               "take_profit_percentage", "sharpe_ratio", "max_drawdown", "total_deals"]].to_string())

    os.makedirs("research/bot_optimization", exist_ok=True)
    out = f"research/bot_optimization/optimize_dca_{args.symbol.replace('/', '_')}.csv"
    results.to_csv(out)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
