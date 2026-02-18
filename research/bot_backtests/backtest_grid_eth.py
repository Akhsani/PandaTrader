"""
S-B: Geometric Sideways Grid — ETH/USDT oscillation harvesting in 20% range.
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from bots.grid_bot import GridBotSimulator
from bots.base_bot import load_ohlcv_for_bot


def load_data(symbol: str, days: int = 730):
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


def run_backtest(
    symbol: str = "ETH/USDT",
    range_pct: float = 0.20,
    grid_lines: int = 20,
    investment: float = 1000,
) -> dict:
    df = load_data(symbol)
    if df is None or len(df) < 100:
        return {"error": "Insufficient data"}

    # Range: ±range_pct around recent price (or 120-day high/low)
    recent = df["close"].iloc[-1]
    roll_high = df["high"].rolling(120).max().dropna()
    roll_low = df["low"].rolling(120).min().dropna()
    if len(roll_high) > 0 and len(roll_low) > 0:
        upper = float(roll_high.iloc[-1])
        lower = float(roll_low.iloc[-1])
    else:
        upper = recent * (1 + range_pct)
        lower = recent * (1 - range_pct)

    params = {
        "upper_price": upper,
        "lower_price": lower,
        "investment_amount": investment,
        "grid_lines_count": grid_lines,
        "grid_type": "geometric",
        "trailing_up": False,
        "expansion_down": False,
        "fee": 0.001,
    }

    bot = GridBotSimulator(params)
    result = bot.run(df, initial_capital=investment)
    result["symbol"] = symbol
    result["period_start"] = str(df.index[0].date())
    result["period_end"] = str(df.index[-1].date())
    result["gate_passed"] = result["sharpe_ratio"] > 1.0 and result["max_drawdown"] > -25
    return result


def main():
    print("=== S-B Geometric Grid (ETH) Backtest ===\n")
    r = run_backtest("ETH/USDT", range_pct=0.20, grid_lines=20)
    if "error" in r:
        print(r["error"])
        return
    print(f"Symbol: {r['symbol']}")
    print(f"Period: {r['period_start']} to {r['period_end']}")
    print(f"Sharpe: {r['sharpe_ratio']:.2f} | MDD: {r['max_drawdown']:.1f}%")
    print(f"Win Rate: {r['win_rate']:.1%} | Deals: {r['total_deals']}")
    print(f"Gate: {'PASSED' if r['gate_passed'] else 'FAILED'}")


if __name__ == "__main__":
    main()
