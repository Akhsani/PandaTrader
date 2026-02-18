"""
Walk-Forward Analysis for Signal Bot strategies.
Usage: python run_wfa_signal.py --strategy sd --symbol BTC/USDT
"""
import sys
import os
import argparse
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from bots.signal_bot import SignalBotSimulator

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_ema(close, period):
    if HAS_TALIB:
        return talib.EMA(close, timeperiod=period)
    return close.ewm(span=period, adjust=False).mean()


def signal_strategy_sd(price_df, funding_df=None, **params):
    """S-D: EMA 12/26 crossover."""
    if price_df is None or len(price_df) < 50:
        return pd.DataFrame()
    df = price_df.copy()
    df.columns = [c.lower() for c in df.columns]
    df["ema12"] = compute_ema(df["close"], 12)
    df["ema26"] = compute_ema(df["close"], 26)
    s = (df["ema12"] > df["ema26"]).shift(1)
    signal = s.where(s.notna(), False).astype(bool)
    bot_params = {
        "position_size": params.get("position_size", 100),
        "take_profit_percentage": params.get("take_profit_percentage", 2.0),
        "stop_loss_percentage": params.get("stop_loss_percentage", 2.0),
        "fee": 0.001,
    }
    bot = SignalBotSimulator(bot_params)
    result = bot.run(df, signal, initial_capital=10000)
    trades = result.get("trades_df", pd.DataFrame())
    if trades.empty:
        return pd.DataFrame()
    return trades[["pnl", "exit_time", "entry_time", "exit_reason"]].copy()


def load_data(symbol, days=730):
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
    parser.add_argument("--strategy", default="sd", choices=["sd", "sg", "sk"])
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--train", type=int, default=365)
    parser.add_argument("--test", type=int, default=90)
    args = parser.parse_args()

    strategy_map = {"sd": signal_strategy_sd}
    strategy_func = strategy_map.get(args.strategy, signal_strategy_sd)

    param_grid = {
        "position_size": [50, 100, 150],
        "take_profit_percentage": [1.5, 2.0, 2.5, 3.0],
        "stop_loss_percentage": [1.5, 2.0, 2.5],
    }

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
    )
    results = analyzer.run()

    if not results.empty:
        total_return = (results["pnl"] + 1).prod() - 1
        win_rate = (results["pnl"] > 0).mean()
        print("\n=== WFA Result (Signal) ===")
        print(f"Strategy: {args.strategy} | Symbol: {args.symbol}")
        print(f"Total Return: {total_return:.2%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        os.makedirs("research/walk_forward/results", exist_ok=True)
        out = f"research/walk_forward/results/wfa_signal_{args.strategy}_{args.symbol.replace('/', '_')}.csv"
        results.to_csv(out)
        print(f"Saved to {out}")
    else:
        print("No trades generated.")


if __name__ == "__main__":
    main()
