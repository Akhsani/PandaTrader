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
from bots.report_utils import write_backtest_report


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

    # Range: use first 120 bars (warmup) — simulates what you'd set at bot launch
    warmup = df.iloc[:120]
    upper = float(warmup["high"].max())
    lower = float(warmup["low"].min())

    # stop_bot_price: 10% below lower — realistic crash protection
    stop_bot_price = lower * 0.90
    params = {
        "upper_price": upper,
        "lower_price": lower,
        "investment_amount": investment,
        "grid_lines_count": grid_lines,
        "grid_type": "geometric",
        "trailing_up": False,
        "expansion_down": False,
        "stop_bot_price": stop_bot_price,
        "fee": 0.001,
    }

    bot = GridBotSimulator(params)
    result = bot.run(df, initial_capital=investment)
    result["symbol"] = symbol
    result["period_start"] = str(df.index[0].date())
    result["period_end"] = str(df.index[-1].date())
    # Grid gate: Cell profit > 3× fees (0.6%), annualized return > 12% (MC ruin < 5% from MC run)
    fee = 0.001
    min_cell_profit = 3 * (2 * fee)  # 3× round-trip fees = 0.006
    grid_deals = [d for d in result.get("closed_deals", []) if d.get("exit_reason") == "grid"]
    mean_cell_profit = np.mean([d["pnl"] for d in grid_deals]) if grid_deals else 0
    ann_ret = result.get("annualized_capital_return", 0)
    result["mean_cell_profit"] = mean_cell_profit
    result["gate_passed"] = mean_cell_profit > min_cell_profit and ann_ret > 12
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
    print(f"Annualized Return: {r.get('annualized_capital_return', 0):.1f}% | Mean Cell Profit: {r.get('mean_cell_profit', 0)*100:.2f}%")
    print(f"Gate: {'PASSED' if r['gate_passed'] else 'FAILED'}")
    report_path = write_backtest_report(
        metrics={
            "sharpe_ratio": r["sharpe_ratio"],
            "max_drawdown": r["max_drawdown"],
            "win_rate": r["win_rate"],
            "total_deals": r["total_deals"],
            "annualized_capital_return": r.get("annualized_capital_return", 0),
            "mean_cell_profit": r.get("mean_cell_profit", 0),
            "gate_passed": r["gate_passed"],
        },
        params=r.get("optimized_params", {}),
        strategy_id="sb",
        symbol=r["symbol"],
        period_start=r["period_start"],
        period_end=r["period_end"],
        out_dir="research/results/backtests",
    )
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
