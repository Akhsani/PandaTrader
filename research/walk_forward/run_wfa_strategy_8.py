"""
Walk-Forward Analysis for Strategy 8: Whale Accumulation Tracker
Uses Nansen TGM flows when API available; falls back to synthetic momentum for historical windows.
"""
import pandas as pd
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.walk_forward.walk_forward_analysis import WalkForwardAnalyzer
from research.backtests.backtest_strategy_8 import (
    load_or_fetch_ohlcv,
    compute_synthetic_accumulation_signal,
    load_nansen_flows_or_synthetic,
    S8_UNIVERSE,
    S8_WFA_PARAMS,
)

# Lazy-init Nansen tracker for WFA (shared across windows)
_wfa_tracker = None

def _get_tracker():
    global _wfa_tracker
    if _wfa_tracker is None:
        from utils.nansen_whale_tracker import NansenWhaleTracker
        _wfa_tracker = NansenWhaleTracker()
    return _wfa_tracker


def strategy_logic_8(price_df, funding_df=None, hold_days=None, threshold=None, lookback=None, symbol=''):
    """
    S8: Whale Accumulation - buy when accumulation signal, hold N days.
    Uses Nansen TGM flows when available; else synthetic. Returns DataFrame with exit_time, pnl, symbol.
    """
    params = S8_WFA_PARAMS
    hold_days = hold_days if hold_days is not None else params['hold_days']
    threshold = threshold if threshold is not None else params['threshold']
    lookback = lookback if lookback is not None else params['lookback']

    if price_df is None or price_df.empty or len(price_df) < 30:
        return None

    tracker = _get_tracker()
    signal, _ = load_nansen_flows_or_synthetic(
        symbol, price_df, tracker, lookback=lookback, require_nansen=False
    )
    if signal is None:
        signal = compute_synthetic_accumulation_signal(price_df, lookback=lookback)

    signal = signal.reindex(price_df.index).fillna(0)
    trades = []
    position = 0
    entry_price = 0
    entry_date = None
    fee = 0.001

    for i in range(1, len(price_df)):
        row = price_df.iloc[i]
        date = price_df.index[i]
        price = row['close']
        sig = signal.iloc[i] if i < len(signal) else 0

        if position > 0:
            days_held = (date - entry_date).days if entry_date else 0
            if days_held >= hold_days or sig == 0:
                ret = (price - entry_price) / entry_price
                pnl = ret - fee * 2
                trades.append({
                    'exit_time': date,
                    'pnl': pnl,
                    'symbol': symbol,
                })
                position = 0
        else:
            if sig >= threshold:
                position = 1
                entry_price = price * (1 + fee)
                entry_date = date

    if not trades:
        return pd.DataFrame()
    out = pd.DataFrame(trades)
    if symbol:
        out['symbol'] = symbol
    return out


def load_data_daily(symbol):
    path_1d = f"data/ohlcv/{symbol.replace('/', '_')}_1d.csv"
    path_1h = f"data/ohlcv/{symbol.replace('/', '_')}_1h.csv"
    if os.path.exists(path_1d):
        from utils.data_loader import load_ohlcv
        return load_ohlcv(path_1d)
    if os.path.exists(path_1h):
        from utils.data_loader import load_ohlcv
        df = load_ohlcv(path_1h)
        return df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    df = load_or_fetch_ohlcv(symbol, days=730, timeframe='1d')
    return df


def run_wfa_for_symbol(symbol, param_grid_base=None):
    """Run WFA for a single symbol."""
    price = load_data_daily(symbol)
    if price is None or len(price) < 200:
        return None, symbol

    param_grid = param_grid_base or {
        'hold_days': [5, 7, 10],
        'threshold': [0.3, 0.5, 0.7],
        'lookback': [5, 7, 14],
    }
    param_grid['symbol'] = [symbol]

    analyzer = WalkForwardAnalyzer(
        strategy_logic_8,
        param_grid,
        price,
        funding_df=None,
        train_window_days=180,
        test_window_days=30,
    )
    return analyzer.run(), symbol


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', default='ETH/USDT')
    parser.add_argument('--pool', action='store_true', help='Run on BTC, ETH, SOL and pool')
    args = parser.parse_args()

    param_grid = {
        'hold_days': [5, 7, 10],
        'threshold': [0.3, 0.5, 0.7],
        'lookback': [5, 7, 14],
    }

    all_results = []
    if args.pool:
        for sym in S8_UNIVERSE:
            print(f"\n--- {sym} ---")
            results, _ = run_wfa_for_symbol(sym, param_grid_base=param_grid)
            if results is not None and not results.empty:
                results['symbol'] = sym
                all_results.append(results)
        results = pd.concat(all_results, ignore_index=True).sort_values('exit_time') if all_results else pd.DataFrame()
    else:
        results, _ = run_wfa_for_symbol(args.symbol, param_grid_base=param_grid)
        results = results if results is not None else pd.DataFrame()

    if not results.empty:
        total_return = (results['pnl'] + 1).prod() - 1
        win_rate = (results['pnl'] > 0).mean()
        print("\n=== Walk-Forward Result (Strategy 8) ===")
        print(f"Total Return: {total_return:.2%}")
        print(f"Win Rate: {win_rate:.2%}")
        print(f"Trades: {len(results)}")
        if 'symbol' in results.columns:
            print(f"By symbol: {results.groupby('symbol').size().to_dict()}")

        os.makedirs("research/walk_forward/results", exist_ok=True)
        filename = f"research/walk_forward/results/wfa_strat8_{'pooled' if args.pool else args.symbol.replace('/', '_')}.csv"
        results.to_csv(filename)
        print(f"Saved to {filename}")
    else:
        print("No trades generated.")
