"""
Strategy 8: On-Chain Whale Accumulation Tracker
Backtest: Buy when Smart Money net inflow > threshold; hold N days; measure vs buy-and-hold.
Uses Nansen token flows when API available; falls back to synthetic momentum proxy otherwise.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_loader import load_ohlcv
from utils.fetch_1h_data import fetch_history

S8_UNIVERSE = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
# Mid-caps (Phase 2 — add after liquid validation)
S8_MIDCAP_UNIVERSE = ['AVAX/USDT', 'LINK/USDT', 'ARB/USDT', 'OP/USDT']

# WFA-optimized params (hold_days=5, threshold=0.3 dominate across assets)
S8_WFA_PARAMS = {'hold_days': 5, 'threshold': 0.3, 'lookback': 7}
TOKEN_MAP = {
    'BTC/USDT': ('ethereum', '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'),
    'ETH/USDT': ('ethereum', '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),
    'SOL/USDT': ('solana', 'So11111111111111111111111111111111111111112'),
    # Mid-caps (Phase 2)
    'AVAX/USDT': ('avalanche', '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'),
    'LINK/USDT': ('ethereum', '0x514910771af9ca656af840dff83e8264ecf986ca'),
    'ARB/USDT': ('arbitrum', '0x912ce59144191c1204e64559fe8253a0e49e6548'),
    'OP/USDT': ('optimism', '0x4200000000000000000000000000000000000042'),
}


def load_or_fetch_ohlcv(symbol, days=730, timeframe='1d'):
    """Load OHLCV from disk or fetch via CCXT. Resamples 1h to 1d if needed."""
    base = symbol.replace('/', '_')
    path_1d = f"data/ohlcv/{base}_1d.csv"
    path_1h = f"data/ohlcv/{base}_1h.csv"
    if os.path.exists(path_1d):
        return load_ohlcv(path_1d)
    if os.path.exists(path_1h):
        df = load_ohlcv(path_1h)
        df = df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
        os.makedirs("data/ohlcv", exist_ok=True)
        df.to_csv(path_1d)
        return df
    print(f"Fetching {symbol}...")
    tf = '1d' if timeframe == '1d' else '1h'
    df = fetch_history(symbol, tf, days)
    if df is None or df.empty:
        return None
    if tf == '1h':
        df = df.resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
    os.makedirs("data/ohlcv", exist_ok=True)
    df.to_csv(path_1d)
    return df


def compute_synthetic_accumulation_signal(df, lookback=7, vol_mult=1.2, use_trend_filter=False):
    """
    Synthetic proxy when Nansen API unavailable: positive momentum + volume confirmation.
    Optional trend filter (close > EMA200) reduces false signals in bear markets.
    Returns series: 1 = accumulation signal, 0 = no signal.
    """
    ret = df['close'].pct_change(lookback)
    vol_ma = df['volume'].rolling(20).mean().replace(0, np.nan)
    vol_spike = (df['volume'] / vol_ma) > vol_mult
    signal = ((ret > 0) & vol_spike).astype(int)
    if use_trend_filter and len(df) >= 200:
        ema200 = df['close'].ewm(span=200, adjust=False).mean()
        signal = signal & (df['close'] > ema200)
    return signal.astype(int)


def load_nansen_flows_or_synthetic(symbol, df, tracker, lookback=7, use_trend_filter=False, require_nansen=False):
    """
    Load flows from Nansen TGM API. Returns (signal, source).
    source: 'nansen' = real Smart Money flows; 'synthetic' = momentum proxy.
    If require_nansen=True, returns (None, None) when real data unavailable.
    """
    if df is None or df.empty or len(df) < 30:
        return None, None
    chain, addr = TOKEN_MAP.get(symbol, (None, None))
    if not chain or not tracker.api_key:
        if require_nansen:
            return None, None
        return compute_synthetic_accumulation_signal(df, lookback=lookback, use_trend_filter=use_trend_filter), 'synthetic'
    date_from = df.index[0].strftime('%Y-%m-%d')
    date_to = df.index[-1].strftime('%Y-%m-%d')
    flows = tracker.get_token_flows(chain, addr, date_from, date_to, label='smart_money')
    if flows is None or flows.empty:
        if require_nansen:
            return None, None
        return compute_synthetic_accumulation_signal(df, lookback=lookback, use_trend_filter=use_trend_filter), 'synthetic'
    # Resample to daily, compute net inflow proxy (inflows - outflows)
    if 'total_inflows_count' in flows.columns and 'total_outflows_count' in flows.columns:
        flows['net_inflow'] = flows['total_inflows_count'] - flows['total_outflows_count']
    else:
        if require_nansen:
            return None, None
        return compute_synthetic_accumulation_signal(df, lookback=lookback, use_trend_filter=use_trend_filter), 'synthetic'
    flows_d = flows.resample('1D').agg({'net_inflow': 'sum'}).reindex(df.index, method='ffill')
    signal = (flows_d['net_inflow'] > 0).astype(int)
    return signal.fillna(0), 'nansen'


def backtest_whale_accumulation(
    df,
    signal,
    init_capital=1000,
    hold_days=7,
    threshold=0.5,
    fee=0.001,
):
    """
    Backtest: buy when signal=1, hold hold_days, sell.
    signal: 1 = accumulation, 0 = no signal. For synthetic, signal is 0/1.
    """
    if df is None or df.empty or signal is None or len(signal) != len(df):
        return None
    signal = signal.reindex(df.index).fillna(0)
    capital = init_capital
    position = 0
    entry_price = 0
    entry_date = None
    equity = [init_capital]
    trades = []

    for i in range(1, len(df)):
        row = df.iloc[i]
        date = df.index[i]
        price = row['close']
        sig = signal.iloc[i] if i < len(signal) else 0

        if position > 0:
            days_held = (date - entry_date).days if entry_date else 0
            if days_held >= hold_days or sig == 0:
                ret = (price - entry_price) / entry_price
                capital *= (1 + ret) * (1 - fee)
                trades.append({'entry': entry_date, 'exit': date, 'ret': ret, 'type': 'hold_exit' if days_held >= hold_days else 'signal_exit'})
                position = 0
            equity.append(capital)
        else:
            if sig >= threshold:
                position = 1
                entry_price = price * (1 + fee)
                entry_date = date
                capital *= (1 - fee)
            equity.append(capital)

    total_return = (capital - init_capital) / init_capital
    days = (df.index[-1] - df.index[0]).days
    apy = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
    eq = pd.Series(equity[:len(df)], index=df.index[:len(equity)])
    peak = eq.cummax()
    max_dd = ((eq - peak) / peak.replace(0, np.nan)).min() if not eq.empty else 0

    bh_return = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]

    return {
        'total_return': total_return,
        'apy': apy,
        'max_drawdown': max_dd,
        'trades': len(trades),
        'buy_hold_return': bh_return,
        'days': days,
        'equity_curve': eq,
    }


def run(include_midcaps=False, use_trend_filter=False, require_nansen=True):
    """
    Run backtest. require_nansen=True (default): use only real Nansen data; skip assets
    where TGM flows unavailable. require_nansen=False (--allow-synthetic): fall back
    to momentum proxy when Nansen unavailable.
    """
    print("Strategy 8: Whale Accumulation Tracker Backtest")
    from utils.nansen_whale_tracker import NansenWhaleTracker

    tracker = NansenWhaleTracker()
    results = {}
    universe = S8_UNIVERSE + (S8_MIDCAP_UNIVERSE if include_midcaps else [])
    skipped = []

    for symbol in universe:
        print(f"\n--- {symbol} ---")
        df = load_or_fetch_ohlcv(symbol, days=365, timeframe='1d')
        if df is None or len(df) < 60:
            print("  Insufficient data")
            continue
        signal, source = load_nansen_flows_or_synthetic(
            symbol, df, tracker,
            lookback=S8_WFA_PARAMS.get('lookback', 7),
            use_trend_filter=use_trend_filter,
            require_nansen=require_nansen,
        )
        if signal is None:
            print("  Skipped (Nansen required, TGM flows unavailable; use --allow-synthetic to include)")
            skipped.append(symbol)
            continue
        print(f"  Signal source: {'Nansen (Smart Money flows)' if source == 'nansen' else 'Synthetic (momentum proxy)'}")

        params = S8_WFA_PARAMS
        bt = backtest_whale_accumulation(
            df, signal,
            hold_days=params['hold_days'],
            threshold=params['threshold'],
        )
        if bt:
            print(f"  Return: {bt['total_return']:.2%} | APY: {bt['apy']:.2%} | MaxDD: {bt['max_drawdown']:.2%} | Trades: {bt['trades']}")
            print(f"  Buy&Hold: {bt['buy_hold_return']:.2%}")
            results[symbol] = bt

    if results:
        avg_ret = np.mean([r['total_return'] for r in results.values()])
        avg_dd = np.mean([r['max_drawdown'] for r in results.values()])
        print(f"\n--- Summary ---")
        print(f"Avg Return: {avg_ret:.2%} | Avg MaxDD: {avg_dd:.2%} | Assets: {list(results.keys())}")
    if skipped and require_nansen:
        print(f"\nSkipped (Nansen required): {', '.join(skipped)}")
        print("  Note: TGM flows may require higher subscription. SOL native unsupported. Use --allow-synthetic to include.")

    return results


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--midcap', action='store_true', help='Include mid-caps (AVAX, LINK, ARB, OP)')
    p.add_argument('--trend-filter', action='store_true', help='Use EMA200 trend filter on synthetic signal')
    p.add_argument('--allow-synthetic', action='store_true', help='Fall back to momentum proxy when Nansen unavailable (default: real data only)')
    args = p.parse_args()
    run(include_midcaps=args.midcap, use_trend_filter=args.trend_filter, require_nansen=not args.allow_synthetic)
