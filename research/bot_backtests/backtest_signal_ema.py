"""
S-D: EMA 12/26 Trend Signal — Long when EMA12 > EMA26 on 1H; exit on TP/SL.
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.signal_bot import SignalBotSimulator
from bots.base_bot import load_ohlcv_for_bot
from bots.report_utils import write_backtest_report

try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False


def compute_ema(close: pd.Series, period: int) -> pd.Series:
    if HAS_TALIB:
        return talib.EMA(close, timeperiod=period)
    return close.ewm(span=period, adjust=False).mean()


def load_data(symbol: str, days: int = 730):
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        return load_ohlcv_for_bot(path)
    from utils.fetch_1h_data import fetch_history
    os.makedirs("data/ohlcv", exist_ok=True)
    df = fetch_history(symbol, timeframe="1h", days=days)
    df.columns = [c.lower() for c in df.columns]
    df.to_csv(path)
    return df


def run_backtest(
    symbol: str = "BTC/USDT",
    trend_filter_sma: int = 200,
    entry_mode: str = "sustained",
    take_profit: float = 2.5,
    stop_loss: float = 2.5,
) -> dict:
    """Run S-D EMA signal backtest. trend_filter_sma=0 disables; 200 = only long when close > SMA200."""
    df = load_data(symbol)
    if df is None or len(df) < 250:
        return {"error": "Insufficient data (need 250+ bars for SMA200)"}

    df["ema12"] = compute_ema(df["close"], 12)
    df["ema26"] = compute_ema(df["close"], 26)
    ema_bull = df["ema12"] > df["ema26"]
    if entry_mode == "crossover":
        s = ema_bull & (df["ema12"].shift(1) <= df["ema26"].shift(1))
    else:
        s = ema_bull
    if trend_filter_sma > 0:
        df["sma"] = df["close"].rolling(trend_filter_sma).mean()
        s = s & (df["close"] > df["sma"])
    s = s.shift(1)
    signal = s.where(s.notna(), False).astype(bool)

    params = {
        "position_size": 100,
        "take_profit_percentage": take_profit,
        "stop_loss_percentage": stop_loss,
        "trailing_stop_loss": False,
        "fee": 0.001,
    }

    bot = SignalBotSimulator(params)
    result = bot.run(df, signal, initial_capital=10000)
    result["symbol"] = symbol
    result["period_start"] = str(df.index[0].date())
    result["period_end"] = str(df.index[-1].date())
    result["gate_passed"] = result["sharpe_ratio"] > 1.0 and result["max_drawdown"] > -25
    return result


def main():
    print("=== S-D EMA 12/26 Trend Signal Backtest ===\n")
    r = run_backtest("BTC/USDT")
    if "error" in r:
        print(r["error"])
        return
    print(f"Symbol: {r['symbol']}")
    print(f"Sharpe: {r['sharpe_ratio']:.2f} | MDD: {r['max_drawdown']:.1f}%")
    print(f"Win Rate: {r['win_rate']:.1%} | Deals: {r['total_deals']}")
    print(f"Gate: {'PASSED' if r['gate_passed'] else 'FAILED'}")
    report_path = write_backtest_report(
        metrics={
            "sharpe_ratio": r["sharpe_ratio"],
            "max_drawdown": r["max_drawdown"],
            "win_rate": r["win_rate"],
            "total_deals": r["total_deals"],
            "gate_passed": r["gate_passed"],
        },
        params=r.get("optimized_params", {}),
        strategy_id="sd",
        symbol=r["symbol"],
        period_start=r["period_start"],
        period_end=r["period_end"],
        out_dir="research/results/backtests",
    )
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
