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


def run_backtest(symbol: str = "BTC/USDT") -> dict:
    df = load_data(symbol)
    if df is None or len(df) < 50:
        return {"error": "Insufficient data"}

    df["ema12"] = compute_ema(df["close"], 12)
    df["ema26"] = compute_ema(df["close"], 26)
    s = (df["ema12"] > df["ema26"]).shift(1)
    signal = s.where(s.notna(), False).astype(bool)

    params = {
        "position_size": 100,
        "take_profit_percentage": 2.0,
        "stop_loss_percentage": 2.0,
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


if __name__ == "__main__":
    main()
