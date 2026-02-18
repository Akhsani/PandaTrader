"""
Strategy 6: Spot-Perp Basis Harvesting (Delta-Neutral Funding Carry)
Phase 2C - Long spot, short perp, collect 8-hour funding.
Exit when 3 consecutive negative funding periods (basis inversion).
"""
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from utils.data_loader import load_ohlcv
from utils.data_collector import fetch_ohlcv, fetch_funding_history


def load_or_fetch_basis_data(symbol, days=730):
    """Load spot, perp, funding; compute basis. Fetch if missing."""
    base = symbol.replace('/', '_')
    spot_path = f"data/ohlcv/{base}_1h.csv"
    perp_path = f"data/ohlcv/{base}_perp_1h.csv"
    funding_path = None
    for p in [f"data/funding_rates/{base}_USDT_funding.csv", f"data/funding_rates/{base}_USDT_USDT_funding.csv",
              f"data/funding_rates/{base}_funding.csv"]:
        if os.path.exists(p):
            funding_path = p
            break
    
    spot = perp = funding = None
    if os.path.exists(spot_path):
        spot = load_ohlcv(spot_path)
        spot = spot[['close']].rename(columns={'close': 'spot_close'})
    if os.path.exists(perp_path):
        perp = load_ohlcv(perp_path)
        perp = perp[['close']].rename(columns={'close': 'perp_close'})
    
    if spot is None:
        print(f"Fetching spot {symbol}...")
        from utils.fetch_1h_data import fetch_history
        spot_df = fetch_history(symbol, '1h', days)
        if spot_df is not None:
            os.makedirs("data/ohlcv", exist_ok=True)
            spot_df.to_csv(spot_path)
            spot = spot_df[['close']].rename(columns={'close': 'spot_close'})
    
    if perp is None:
        print(f"Fetching perp {symbol}...")
        from utils.fetch_1h_data import fetch_perp_ohlcv
        perp_df = fetch_perp_ohlcv(symbol, '1h', days)
        if perp_df is not None:
            os.makedirs("data/ohlcv", exist_ok=True)
            perp_df.to_csv(perp_path)
            perp = perp_df[['close']].rename(columns={'close': 'perp_close'})
    
    if perp is None and spot is not None:
        perp = spot.copy().rename(columns={'spot_close': 'perp_close'})
    
    if os.path.exists(funding_path):
        funding = pd.read_csv(funding_path, index_col=0, parse_dates=True)
    else:
        print(f"Fetching funding for {symbol}...")
        from utils.fetch_1h_data import fetch_funding
        funding_sym = symbol + ':USDT' if ':' not in symbol else symbol
        fd = fetch_funding(funding_sym, days)
        if fd is not None and not fd.empty:
            os.makedirs("data/funding_rates", exist_ok=True)
            save_path = f"data/funding_rates/{base}_USDT_USDT_funding.csv"
            fd.to_csv(save_path)
            funding = fd
    
    if spot is None or perp is None:
        return None
    
    merged = spot.join(perp, how='inner')
    merged['basis'] = (merged['spot_close'] - merged['perp_close']) / merged['perp_close'].replace(0, np.nan)
    merged['basis'] = merged['basis'].fillna(0)
    
    if funding is not None and not funding.empty:
        fr_col = [c for c in funding.columns if 'funding' in c.lower() or 'rate' in c.lower()]
        fr_col = fr_col[0] if fr_col else funding.columns[0]
        fr = funding[fr_col].rename('funding_rate')
        fr = fr[~fr.index.duplicated(keep='last')]
        merged = merged.join(fr.reindex(merged.index, method='ffill'), how='left')
        merged['funding_rate'] = merged['funding_rate'].fillna(0)
    else:
        merged['funding_rate'] = 0.0
    
    return merged


def backtest_basis_harvest(df, init_capital=1000, fee=0.0005, neg_streak_exit=3, entry_threshold=0.00005, capital_pct=1.0):
    """
    Backtest: Long spot, short perp. Collect funding every 8h.
    Exit when `neg_streak_exit` consecutive negative funding periods (basis inversion).
    Entry when funding > entry_threshold.
    capital_pct: fraction of capital deployed to funding (1.0 = 100%).
    """
    if df is None or len(df) < 100:
        return None
    
    df_8h = df.resample('8h').agg({
        'spot_close': 'last',
        'perp_close': 'last',
        'basis': 'last',
        'funding_rate': 'last'
    }).dropna()
    
    capital = init_capital
    position = 0
    neg_funding_streak = 0
    equity_curve = [init_capital]
    
    for i in range(1, len(df_8h)):
        row = df_8h.iloc[i]
        funding = float(row['funding_rate']) if pd.notna(row['funding_rate']) else 0.0
        
        if funding < 0:
            neg_funding_streak += 1
        else:
            neg_funding_streak = 0
        
        if position == 1:
            # Collect funding: short perp receives when funding > 0
            capital += capital * funding * capital_pct
            equity_curve.append(capital)
            if neg_funding_streak >= neg_streak_exit:
                position = 0
                neg_funding_streak = 0
        else:
            if funding > entry_threshold and neg_funding_streak == 0:
                position = 1
            equity_curve.append(capital)
    
    total_return = (capital - init_capital) / init_capital
    days = (df_8h.index[-1] - df_8h.index[0]).days
    apy = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
    
    idx = df_8h.index[:len(equity_curve)]
    eq = pd.Series(equity_curve[:len(idx)], index=idx)
    peak = eq.cummax()
    dd = (eq - peak) / peak.replace(0, np.nan)
    max_dd = dd.min() if not dd.isna().all() else 0
    
    return {
        'total_return': total_return,
        'apy': apy,
        'max_drawdown': max_dd,
        'final_capital': capital,
        'days': days,
        'equity_curve': eq
    }


def run():
    print("Strategy 6: Spot-Perp Basis Harvesting Backtest")
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    results = {}
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        df = load_or_fetch_basis_data(symbol)
        if df is None:
            print("  No data")
            continue
        bt = backtest_basis_harvest(df)
        if bt:
            print(f"  Return: {bt['total_return']:.2%} | APY: {bt['apy']:.2%} | MaxDD: {bt['max_drawdown']:.2%}")
            results[symbol] = bt
    
    if results:
        avg_ret = np.mean([r['total_return'] for r in results.values()])
        avg_dd = np.mean([r['max_drawdown'] for r in results.values()])
        print(f"\n--- Summary ---")
        print(f"Avg Return: {avg_ret:.2%} | Avg MaxDD: {avg_dd:.2%}")
    
    return results


if __name__ == "__main__":
    run()
