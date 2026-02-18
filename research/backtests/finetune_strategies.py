"""
Fine-tuning experiments per PHASE_2B_2C_IMPROVEMENT_REPORT recommendations.
Runs parameter sweeps for S6, S9; reoptimizes S2; pools S1 Mon-Wed.
Run from project root: python research/backtests/finetune_strategies.py
"""
import sys
import os
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# --- S6 imports ---
from research.backtests.backtest_strategy_6 import load_or_fetch_basis_data, backtest_basis_harvest

# --- S9 imports ---
from research.backtests.backtest_strategy_9 import (
    S9_UNIVERSE, load_funding_multi, compute_zscore_ranking
)


def backtest_rotation_tunable(funding_dict, init_capital=1000, window=90,
                              z_entry=0.5, z_exit=0.5, capital_pct=0.1):
    """S9 backtest with tunable Z thresholds and capital deployment."""
    if len(funding_dict) < 2:
        return None
    zdf = compute_zscore_ranking(funding_dict, window)
    zdf = zdf.dropna(how='all')
    capital = init_capital
    position = None
    equity = [init_capital]
    for i in range(window, len(zdf)):
        row = zdf.iloc[i]
        valid = row.dropna()
        if valid.empty:
            equity.append(capital)
            continue
        if position is not None:
            sym, _ = position
            curr_z = row.get(sym, 0)
            if pd.isna(curr_z) or curr_z < z_exit:
                funding = funding_dict[sym].reindex(zdf.index).ffill().iloc[i]
                capital += capital * float(funding) * capital_pct
                position = None
            else:
                funding = funding_dict[sym].reindex(zdf.index).ffill().iloc[i]
                capital += capital * float(funding) * capital_pct
        else:
            best = valid.idxmax()
            best_z = valid[best]
            if best_z > z_entry:
                position = (best, best_z)
        equity.append(capital)
    total_return = (capital - init_capital) / init_capital
    days = (zdf.index[-1] - zdf.index[window]).days
    apy = (1 + total_return) ** (365 / max(days, 1)) - 1 if days > 0 else 0
    eq = pd.Series(equity, index=zdf.index[window-1:window-1+len(equity)])
    peak = eq.cummax()
    max_dd = ((eq - peak) / peak.replace(0, np.nan)).min()
    return {'total_return': total_return, 'apy': apy, 'max_drawdown': max_dd, 'days': days}


def run_s6_finetune():
    """S6: Relax exit rule (3->4,5,6), lower entry threshold, capital deployment."""
    print("\n" + "="*60)
    print("S6 FINE-TUNING: Basis Harvest")
    print("="*60)
    
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    data = {}
    for sym in symbols:
        df = load_or_fetch_basis_data(sym)
        if df is not None:
            data[sym] = df
    
    if not data:
        print("No S6 data available.")
        return {}
    
    results = []
    # Baseline: neg_streak=3, entry=0.0001, capital_pct=1.0
    for neg_exit in [3, 4, 5, 6]:
        for entry_thresh in [0.00005, 0.0001, 0.0002]:
            for cap_pct in [0.5, 1.0]:
                rets = []
                for sym, df in data.items():
                    bt = backtest_basis_harvest(df, neg_streak_exit=neg_exit,
                                                entry_threshold=entry_thresh,
                                                capital_pct=cap_pct)
                    if bt:
                        rets.append(bt['total_return'])
                if rets:
                    avg_ret = np.mean(rets)
                    results.append({
                        'neg_exit': neg_exit, 'entry_thresh': entry_thresh,
                        'cap_pct': cap_pct, 'avg_return': avg_ret,
                        'avg_apy': (1+avg_ret)**(365/730)-1 if avg_ret > -1 else 0
                    })
    
    # Sort by return
    results = sorted(results, key=lambda x: x['avg_return'], reverse=True)
    print("\nTop 10 S6 parameter combinations:")
    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. neg_exit={r['neg_exit']} entry={r['entry_thresh']} cap={r['cap_pct']} -> Return={r['avg_return']:.2%} APY={r['avg_apy']:.2%}")
    
    best = results[0] if results else None
    return {'s6': results, 'best': best}


def run_s9_finetune():
    """S9: Z entry/exit thresholds, capital deployment."""
    print("\n" + "="*60)
    print("S9 FINE-TUNING: Cross-Asset Funding Rotation")
    print("="*60)
    
    symbols = [s for s in S9_UNIVERSE if os.path.exists(os.path.join(PROJECT_ROOT, f"data/funding_rates/{s.replace('/', '_')}_USDT_USDT_funding.csv"))
               or os.path.exists(os.path.join(PROJECT_ROOT, f"data/funding_rates/{s.replace('/', '_')}_funding.csv"))]
    if len(symbols) < 2:
        funding_dict = load_funding_multi(S9_UNIVERSE[:5])
        symbols = list(funding_dict.keys())
    else:
        funding_dict = load_funding_multi(symbols)
    
    if len(funding_dict) < 2:
        print("Need at least 2 assets. Available:", len(funding_dict))
        return {}
    
    print(f"Assets: {list(funding_dict.keys())}")
    
    results = []
    for z_entry in [0.3, 0.5, 0.7]:
        for z_exit in [0.3, 0.5]:
            for cap_pct in [0.2, 0.5, 1.0]:
                r = backtest_rotation_tunable(funding_dict, z_entry=z_entry,
                                              z_exit=z_exit, capital_pct=cap_pct)
                if r:
                    results.append({
                        'z_entry': z_entry, 'z_exit': z_exit, 'cap_pct': cap_pct,
                        **r
                    })
    
    results = sorted(results, key=lambda x: x['total_return'], reverse=True)
    print("\nTop 10 S9 parameter combinations:")
    for i, r in enumerate(results[:10]):
        print(f"  {i+1}. z_entry={r['z_entry']} z_exit={r['z_exit']} cap={r['cap_pct']} -> Return={r['total_return']:.2%} APY={r['apy']:.2%}")
    
    return {'s9': results, 'best': results[0] if results else None}


def run_s2_reoptimize():
    """S2: Run reoptimize and show latest params."""
    print("\n" + "="*60)
    print("S2 REOPTIMIZE: Funding Reversion (ETH)")
    print("="*60)
    
    try:
        import subprocess
        out_path = os.path.join(PROJECT_ROOT, 'research/walk_forward/results/strategy2_params.json')
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        out = subprocess.run(
            [sys.executable, 'research/walk_forward/reoptimize_strategy_2.py', '--symbol', 'ETH/USDT',
             '--output', out_path],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=120000
        )
        print(out.stdout)
        if out.stderr:
            print("Stderr:", out.stderr)
        if os.path.exists(out_path):
            import json
            with open(out_path) as f:
                params = json.load(f)
            print("\nOptimized params:", params)
            return {'s2': params}
    except Exception as e:
        print(f"S2 reoptimize error: {e}")
    return {}


def run_s1_pooled_monwed():
    """S1: Run pooled Mon-Wed variant."""
    print("\n" + "="*60)
    print("S1 POOLED MON-WED: Weekend Momentum Variant")
    print("="*60)
    
    try:
        import subprocess
        out = subprocess.run(
            [sys.executable, 'research/walk_forward/run_wfa_strategy_1.py', '--pool', '--variant', 'mon-wed'],
            cwd=PROJECT_ROOT,
            capture_output=True, text=True, timeout=120000
        )
        print(out.stdout)
        if out.returncode != 0:
            print("Stderr:", out.stderr)
        # Parse output for summary
        if 'Total Return' in out.stdout:
            for line in out.stdout.split('\n'):
                if 'Total Return' in line or 'Win Rate' in line or 'Trades' in line:
                    print(line.strip())
        return {'s1_monwed': 'completed'}
    except Exception as e:
        print(f"S1 error: {e}")
    return {}


def main():
    print("FINE-TUNING EXPERIMENTS (per Improvement Report)")
    all_results = {}
    
    all_results.update(run_s6_finetune())
    all_results.update(run_s9_finetune())
    all_results.update(run_s2_reoptimize())
    all_results.update(run_s1_pooled_monwed())
    
    return all_results


if __name__ == "__main__":
    main()
