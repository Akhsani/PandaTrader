"""
S-E: Futures Grid BTC 2x Reversal — Both directions within range.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.grid_bot import GridBotSimulator
from bots.base_bot import load_ohlcv_for_bot


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
    if df is None or len(df) < 200:
        return {"error": "Insufficient data"}
    roll_high = df["high"].rolling(120).max().iloc[-1]
    roll_low = df["low"].rolling(120).min().iloc[-1]
    stop_bot_price = roll_low * 0.90
    params = {
        "upper_price": roll_high,
        "lower_price": roll_low,
        "investment_amount": 1000,
        "grid_lines_count": 20,
        "grid_type": "geometric",
        "trailing_up": False,
        "stop_bot_price": stop_bot_price,
        "leverage": 2,
        "fee": 0.0005,
    }
    bot = GridBotSimulator(params)
    result = bot.run(df, initial_capital=1000)
    result["symbol"] = symbol
    result["gate_passed"] = result["sharpe_ratio"] > 1.0 and result["max_drawdown"] > -25
    return result


if __name__ == "__main__":
    r = run_backtest("BTC/USDT")
    print("S-E Grid Reversal:", r.get("sharpe_ratio", 0), r.get("total_deals", 0))
