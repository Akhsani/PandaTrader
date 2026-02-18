"""
S-A: RSI Oversold DCA — RSI-7 < 20 triggers entry; mean reversion to TP 2.5%.
Backtest on BTC, ETH, SOL.
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.dca_bot import DCABotSimulator
from bots.base_bot import load_ohlcv_for_bot
from bots.report_utils import write_backtest_report

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_rsi(close: pd.Series, period: int = 7) -> pd.Series:
    """RSI with talib or fallback."""
    if HAS_TALIB:
        rsi = talib.RSI(close, timeperiod=period)
    else:
        delta = close.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def load_data(symbol: str, days: int = 730):
    """Load 1h OHLCV. Try local first, then fetch."""
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        return load_ohlcv_for_bot(path)
    print(f"Fetching {symbol}...")
    from utils.fetch_1h_data import fetch_history
    os.makedirs("data/ohlcv", exist_ok=True)
    df = fetch_history(symbol, timeframe="1h", days=days)
    df.columns = [c.lower() for c in df.columns]
    df.to_csv(path)
    return df


def run_backtest(symbol: str, initial_capital: float = 10000.0) -> dict:
    """Run S-A RSI DCA backtest for one symbol."""
    df = load_data(symbol)
    if df is None or len(df) < 50:
        return {"error": f"Insufficient data for {symbol}"}

    df["rsi"] = compute_rsi(df["close"], period=7)
    signal = df["rsi"] < 20
    # Shift: signal at bar i means we open at bar i+1 open
    signal = signal.shift(1)
    signal = signal.where(signal.notna(), False).astype(bool)

    params = {
        "base_order_volume": 25,
        "safety_order_volume": 30,
        "max_safety_orders": 4,
        "safety_order_step_percentage": 0.75,
        "martingale_volume_coefficient": 2.0,
        "martingale_step_coefficient": 1.5,
        "take_profit_percentage": 2.5,
        "stop_loss_percentage": 15.0,  # Realistic: cut loss if avg price drops 15%
        "trailing_take_profit": False,
        "max_active_deals": 1,
        "cooldown_between_deals": 0,
        "fee": 0.001,
    }

    bot = DCABotSimulator(params)
    result = bot.run(df, signal, initial_capital=initial_capital)

    result["symbol"] = symbol
    result["period_start"] = str(df.index[0].date())
    result["period_end"] = str(df.index[-1].date())
    result["gate_passed"] = (
        result["sharpe_ratio"] > 1.0 and result["max_drawdown"] > -25
    )
    return result


def main():
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    print("=== S-A RSI Oversold DCA Backtest ===\n")

    all_results = []
    for sym in symbols:
        try:
            r = run_backtest(sym)
            if "error" in r:
                print(f"{sym}: {r['error']}")
                continue
            all_results.append(r)
            print(f"{sym}:")
            print(f"  Sharpe: {r['sharpe_ratio']:.2f} | MDD: {r['max_drawdown']:.1f}%")
            print(f"  Win Rate: {r['win_rate']:.1%} | Deals: {r['total_deals']}")
            print(f"  Avg Duration: {r['avg_deal_duration_hours']:.0f}h")

            if r["gate_passed"]:
                print(f"  Gate: PASSED (Sharpe>1.0, MDD<25%)")
            else:
                print(f"  Gate: FAILED")
            report_path = write_backtest_report(
                metrics={
                    "sharpe_ratio": r["sharpe_ratio"],
                    "max_drawdown": r["max_drawdown"],
                    "win_rate": r["win_rate"],
                    "total_deals": r["total_deals"],
                    "gate_passed": r["gate_passed"],
                },
                params=r.get("optimized_params", {}),
                strategy_id="sa",
                symbol=sym,
                period_start=r["period_start"],
                period_end=r["period_end"],
                out_dir="research/results/backtests",
            )
            print(f"  Report: {report_path}")
            print()
        except Exception as e:
            print(f"{sym}: Error - {e}\n")

    if all_results:
        avg_sharpe = np.mean([r["sharpe_ratio"] for r in all_results])
        avg_mdd = np.mean([r["max_drawdown"] for r in all_results])
        total_deals = sum(r["total_deals"] for r in all_results)
        print("--- Summary ---")
        print(f"Avg Sharpe: {avg_sharpe:.2f} | Avg MDD: {avg_mdd:.1f}%")
        print(f"Total Deals: {total_deals}")


if __name__ == "__main__":
    main()
