"""
Report generation helpers for bot backtests, WFA, and Monte Carlo.
"""
import os
import json
import numpy as np
from datetime import datetime
from typing import Optional, Any
import pandas as pd


def _json_safe(obj: Any) -> Any:
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return obj


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


def write_backtest_report(
    metrics: dict,
    params: dict,
    strategy_id: str,
    symbol: str,
    period_start: str,
    period_end: str,
    out_dir: str = "research/results/backtests",
) -> str:
    """Write backtest JSON report."""
    bot_type = "dca" if "base_order_volume" in params else "grid" if "upper_price" in params else "signal"
    subdir = "dca" if "base_order_volume" in params else "grid" if "upper_price" in params else "signal"
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{strategy_id}_{symbol.replace('/', '_')}_{date_str}.json"
    path = os.path.join(out_dir, subdir, filename)
    _ensure_dir(path)
    payload = {
        "strategy_id": strategy_id,
        "symbol": symbol,
        "period_start": period_start,
        "period_end": period_end,
        "params": _json_safe(params),
        "metrics": _json_safe(metrics),
        "gate_passed": bool(metrics.get("gate_passed", False)),
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def write_wfa_report(
    trades_df: pd.DataFrame,
    summary: dict,
    strategy_id: str,
    symbol: str,
    out_dir: str = "research/results/walk_forward",
) -> tuple:
    """Write WFA CSV and summary JSON."""
    subdir = "dca" if "degradation_ratio" in summary else "grid" if "grid" in strategy_id else "signal"
    date_str = datetime.now().strftime("%Y%m%d")
    base = f"wfa_{strategy_id}_{symbol.replace('/', '_')}_{date_str}"
    csv_path = os.path.join(out_dir, subdir, f"{base}.csv")
    json_path = os.path.join(out_dir, subdir, f"{base}_summary.json")
    _ensure_dir(csv_path)
    if not trades_df.empty:
        trades_df.to_csv(csv_path, index=False)
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    return csv_path, json_path


def write_mc_report(
    stats: dict,
    strategy_id: str,
    symbol: str,
    out_dir: str = "research/results/monte_carlo",
) -> tuple:
    """Write Monte Carlo JSON and human-readable TXT."""
    subdir = "dca" if "dca" in strategy_id else "grid" if "grid" in strategy_id else "signal"
    date_str = datetime.now().strftime("%Y%m%d")
    base = f"mc_{strategy_id}_{symbol.replace('/', '_')}_{date_str}"
    json_path = os.path.join(out_dir, subdir, f"{base}.json")
    txt_path = os.path.join(out_dir, subdir, f"{base}.txt")
    _ensure_dir(json_path)
    with open(json_path, "w") as f:
        json.dump(stats, f, indent=2)
    with open(txt_path, "w") as f:
        f.write("=== Monte Carlo Simulation Results ===\n")
        for k, v in stats.items():
            f.write(f"{k}: {v}\n")
    return json_path, txt_path


def generate_strategy_report(
    strategy_id: str,
    strategy_name: str,
    backtest_path: Optional[str] = None,
    wfa_path: Optional[str] = None,
    mc_path: Optional[str] = None,
    out_dir: str = "research/reports/strategies",
) -> str:
    """Assemble EXP_BOT_*.md from template."""
    _ensure_dir(out_dir)
    path = os.path.join(out_dir, f"EXP_BOT_{strategy_id.upper()}.md")
    content = f"""# EXP_BOT: {strategy_name}

## 1. Hypothesis
See crypto-bot-strategy-3.md for strategy hypothesis.

## 2. Methodology
- **Bot Type**: DCA / Grid / Signal (as applicable)
- **Strategy ID**: {strategy_id}
- **Data**: 1h OHLCV from Binance

## 3. Results

### A. Backtest
- Backtest report: {backtest_path or 'N/A'}

### B. Walk-Forward Analysis
- WFA report: {wfa_path or 'N/A'}

### C. Monte Carlo Validation
- MC report: {mc_path or 'N/A'}

## 4. Conclusion
[Approved / Needs Revision / Rejected]

## 5. 3Commas Export Params
Use `bots.export_config.export_to_3commas()` with optimized_params.

## 6. Next Steps
- Paper trade on 3Commas
- Re-optimize monthly
"""
    with open(path, "w") as f:
        f.write(content)
    return path
