"""
S-C: BB Lower Band + RSI Composite DCA — Dual-confirmation entry.
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.dca_bot import DCABotSimulator
from bots.base_bot import load_ohlcv_for_bot

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
    rs = gain.rolling(period).mean() / loss.rolling(period).mean().replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(50)


def compute_bb(close, period=20):
    if HAS_TALIB:
        upper, mid, lower = talib.BBANDS(close, timeperiod=period)
        return lower
    sma = close.rolling(period).mean()
    std = close.rolling(period).std()
    return sma - 2 * std


def load_data(symbol, days=730):
    path = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path):
        return load_ohlcv_for_bot(path)
    from utils.fetch_1h_data import fetch_history
    os.makedirs("data/ohlcv", exist_ok=True)
    df = fetch_history(symbol, timeframe="1h", days=days)
    df.columns = [c.lower() for c in df.columns]
    df.to_csv(path)
    return df


def run_backtest(symbol="BTC/USDT"):
    df = load_data(symbol)
    if df is None or len(df) < 50:
        return {"error": "Insufficient data"}
    df["rsi"] = compute_rsi(df["close"], 7)
    df["bb_lower"] = compute_bb(df["close"], 20)
    s = ((df["close"] <= df["bb_lower"]) & (df["rsi"] < 30)).shift(1)
    signal = s.where(s.notna(), False).astype(bool)
    params = {
        "base_order_volume": 25,
        "safety_order_volume": 30,
        "max_safety_orders": 4,
        "safety_order_step_percentage": 0.75,
        "martingale_volume_coefficient": 2.0,
        "martingale_step_coefficient": 1.5,
        "take_profit_percentage": 2.5,
        "stop_loss_percentage": 15.0,
        "fee": 0.001,
    }
    bot = DCABotSimulator(params)
    result = bot.run(df, signal, initial_capital=10000)
    result["symbol"] = symbol
    result["gate_passed"] = result["sharpe_ratio"] > 1.0 and result["max_drawdown"] > -25
    return result


if __name__ == "__main__":
    r = run_backtest("BTC/USDT")
    print("S-C BB+RSI:", r.get("sharpe_ratio", 0), r.get("total_deals", 0))
