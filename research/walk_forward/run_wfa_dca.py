"""
Walk-Forward Analysis for DCA Bot strategies.
Usage: python run_wfa_dca.py --strategy sa --symbol BTC/USDT
Strategies: sa (RSI), sc (BB+RSI), sf (Heikin Ashi), sh (QFL), si (MACD), sj (Stochastic), sl (RSI Pyramid)
"""
import sys
import os
import argparse
import pandas as pd
import numpy as np
import itertools

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from bots.dca_bot import DCABotSimulator


def _make_regime_gate_hook():
    """Return pre_test_hook that skips DCA when test window regime is BEAR (mean reversion fails)."""
    def hook(train_price, test_price, best_params):
        try:
            from utils.regime_detector import CryptoRegimeDetector
            det = CryptoRegimeDetector(n_regimes=4)
            det.fit(train_price)
            regime = det.current_regime(test_price)
            if regime == "BEAR":
                return False  # Skip DCA in bear regime
        except Exception as e:
            print(f"    Regime gate warning: {e}, proceeding")
        return True
    return hook


try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_rsi(close: pd.Series, period: int = 7) -> pd.Series:
    if HAS_TALIB:
        return talib.RSI(close, timeperiod=period).fillna(50)
    delta = close.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def dca_strategy_sa(price_df: pd.DataFrame, funding_df=None, **params) -> pd.DataFrame:
    """S-A: RSI-7 < 20 signal. regime_gate: block entries when regime is BEAR."""
    if price_df is None or len(price_df) < 50:
        return pd.DataFrame()
    df = price_df.copy()
    df.columns = [c.lower() for c in df.columns]
    df["rsi"] = compute_rsi(df["close"], period=7)
    s = (df["rsi"] < 20).shift(1)
    signal = s.where(s.notna(), False).astype(bool)
    if params.get("regime_gate"):
        try:
            from utils.regime_detector import CryptoRegimeDetector
            det = CryptoRegimeDetector(n_regimes=4)
            det.fit(df)
            df_regime = det.predict(df)
            regime_ok = df_regime["regime_label"] != "BEAR"
            regime_ok = regime_ok.reindex(signal.index, fill_value=True)
            signal = signal & regime_ok
        except Exception:
            pass
    bot_params = {
        "base_order_volume": params.get("base_order_volume", 25),
        "safety_order_volume": params.get("safety_order_volume", 30),
        "max_safety_orders": params.get("max_safety_orders", 4),
        "safety_order_step_percentage": params.get("safety_order_step_percentage", 0.75),
        "martingale_volume_coefficient": params.get("martingale_volume_coefficient", 2.0),
        "martingale_step_coefficient": params.get("martingale_step_coefficient", 1.5),
        "take_profit_percentage": params.get("take_profit_percentage", 2.5),
        "stop_loss_percentage": params.get("stop_loss_percentage", 15.0),
        "trailing_take_profit": params.get("trailing_take_profit", False),
        "max_active_deals": 1,
        "cooldown_between_deals": 0,
        "fee": 0.001,
    }
    bot = DCABotSimulator(bot_params)
    result = bot.run(df, signal, initial_capital=10000)
    trades = result.get("trades_df", pd.DataFrame())
    if trades.empty:
        return pd.DataFrame()
    return trades[["pnl", "exit_time", "entry_time", "exit_reason"]].copy()


def load_data(symbol: str, days: int = 730) -> pd.DataFrame:
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=["datetime"], index_col="datetime")
    else:
        from utils.fetch_1h_data import fetch_history
        os.makedirs("data/ohlcv", exist_ok=True)
        df = fetch_history(symbol, timeframe="1h", days=days)
    df.columns = [c.lower() for c in df.columns]
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="sa", choices=["sa", "sc", "sf", "sh", "si", "sj", "sl"])
    parser.add_argument("--symbol", default="BTC/USDT")
    parser.add_argument("--train", type=int, default=365)
    parser.add_argument("--test", type=int, default=90)
    parser.add_argument("--fast", action="store_true", help="Reduced param grid for faster runs")
    parser.add_argument("--pool", action="store_true", help="Run WFA on BTC, ETH, SOL and pool OOS trades")
    parser.add_argument("--regime-gate", action="store_true",
                        help="Block DCA entries when regime is BEAR; skip test windows in BEAR")
    args = parser.parse_args()

    strategy_map = {"sa": dca_strategy_sa}
    strategy_func = strategy_map.get(args.strategy, dca_strategy_sa)

    if args.fast:
        param_grid = {
            "base_order_volume": [25],
            "safety_order_volume": [30],
            "max_safety_orders": [4],
            "safety_order_step_percentage": [0.75],
            "martingale_volume_coefficient": [2.0],
            "martingale_step_coefficient": [1.5],
            "take_profit_percentage": [2.5],
            "stop_loss_percentage": [15.0],
        }
    else:
        param_grid = {
            "base_order_volume": [25],
            "safety_order_volume": [30],
            "max_safety_orders": [4],
            "safety_order_step_percentage": [0.75],
            "martingale_volume_coefficient": [2.0],
            "martingale_step_coefficient": [1.5],
            "take_profit_percentage": [2.0, 2.5],
            "stop_loss_percentage": [12.0, 15.0, 18.0],
        }
    if args.regime_gate:
        param_grid["regime_gate"] = [True]

    pre_test_hook = _make_regime_gate_hook() if args.regime_gate else None

    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"] if args.pool else [args.symbol]
    all_results = []
    for sym in symbols:
        price_df = load_data(sym)
        if price_df is None or len(price_df) < 500:
            print(f"Insufficient data for {sym}.")
            continue
        print(f"\n--- WFA {sym} ---")
        analyzer = WalkForwardAnalyzer(
            strategy_func,
            param_grid,
            price_df,
            funding_df=None,
            train_window_days=args.train,
            test_window_days=args.test,
            pre_test_hook=pre_test_hook,
        )
        res = analyzer.run()
        if not res.empty:
            res["symbol"] = sym
            all_results.append(res)

    if args.pool and all_results:
        results = pd.concat(all_results, ignore_index=True)
        results = results.sort_values("exit_time")
    elif all_results:
        results = all_results[0]
    else:
        results = pd.DataFrame()

    if not results.empty:
        total_return = (results["pnl"] + 1).prod() - 1
        win_rate = (results["pnl"] > 0).mean()
        ev_per_deal = results["pnl"].mean()
        print("\n=== WFA Result (DCA) ===")
        print(f"Strategy: {args.strategy} | Symbol(s): {symbols}")
        print(f"Total Return: {total_return:.2%}")
        print(f"EV per deal: {ev_per_deal:.4f}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        if "symbol" in results.columns:
            print(f"By symbol: {results.groupby('symbol').size().to_dict()}")
        os.makedirs("research/walk_forward/results", exist_ok=True)
        if args.pool:
            out = f"research/walk_forward/results/wfa_dca_{args.strategy}_pooled.csv"
        else:
            out = f"research/walk_forward/results/wfa_dca_{args.strategy}_{args.symbol.replace('/', '_')}.csv"
        results.to_csv(out)
        print(f"Saved to {out}")
    else:
        print("No trades generated.")


if __name__ == "__main__":
    main()
