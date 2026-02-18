"""
Bayesian optimization for DCA bot parameters using Optuna.
Objective: maximize per-deal EV × win_rate (NOT Sharpe).
"""
import sys
import os
import argparse
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.dca_bot import DCABotSimulator

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False

try:
    import optuna
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--trials", type=int, default=200)
    parser.add_argument("--capital", type=float, default=10000)
    args = parser.parse_args()

    if not HAS_OPTUNA:
        print("Optuna not installed. Run: pip install optuna")
        return

    print(f"Loading {args.symbol}...")
    df = load_data(args.symbol)
    if df is None or len(df) < 100:
        print("Insufficient data.")
        return

    df["rsi"] = compute_rsi(df["close"], 7)
    s = (df["rsi"] < 20).shift(1)
    signal = s.where(s.notna(), False).astype(bool)

    ohlcv = df
    initial_capital = args.capital

    def objective(trial):
        params = {
            "base_order_volume": trial.suggest_float("base_order_volume", 15, 50),
            "safety_order_volume": trial.suggest_float("safety_order_volume", 20, 80),
            "max_safety_orders": trial.suggest_int("max_safety_orders", 2, 7),
            "safety_order_step_percentage": trial.suggest_float("safety_order_step", 0.3, 2.0),
            "martingale_volume_coefficient": trial.suggest_float("mv_coeff", 1.2, 3.0),
            "martingale_step_coefficient": trial.suggest_float("ms_coeff", 1.0, 2.5),
            "take_profit_percentage": trial.suggest_float("tp_pct", 1.0, 4.0),
            "stop_loss_percentage": trial.suggest_float("sl_pct", 8.0, 25.0),
            "trailing_take_profit": False,
            "max_active_deals": 1,
            "cooldown_between_deals": 0,
            "fee": 0.001,
        }
        bot = DCABotSimulator(params)
        result = bot.run(ohlcv, signal, initial_capital=initial_capital)

        total_deals = result.get("total_deals", 0)
        if total_deals < 10:
            return -999.0

        ev = result.get("expected_value_per_deal", 0)
        win_rate = result.get("win_rate", 0)
        if ev is None:
            ev = 0
        return float(ev * win_rate * 100)

    print(f"Running Optuna optimization ({args.trials} trials)...")
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=args.trials, show_progress_bar=True)

    best = study.best_params
    print(f"\nBest params: {best}")
    print(f"Best score: {study.best_value:.4f}")

    # Run once with best params to get full metrics
    full_params = {
        **best,
        "trailing_take_profit": False,
        "max_active_deals": 1,
        "cooldown_between_deals": 0,
        "fee": 0.001,
    }
    bot = DCABotSimulator(full_params)
    result = bot.run(ohlcv, signal, initial_capital=initial_capital)
    print(f"\nMetrics with best params:")
    print(f"  EV per deal: {result.get('expected_value_per_deal', 0):.4f}")
    print(f"  Win Rate: {result.get('win_rate', 0):.1%}")
    print(f"  Total Deals: {result.get('total_deals', 0)}")
    print(f"  Sharpe: {result.get('sharpe_ratio', 0):.2f}")
    print(f"  Max Drawdown: {result.get('max_drawdown', 0):.1f}%")

    os.makedirs("research/bot_optimization", exist_ok=True)
    out = f"research/bot_optimization/optimize_dca_bayesian_{args.symbol.replace('/', '_')}.json"
    import json
    with open(out, "w") as f:
        json.dump({"best_params": best, "best_score": study.best_value}, f, indent=2)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
