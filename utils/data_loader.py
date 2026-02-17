"""
Shared data loading utilities. Handles datetime vs date column naming across scripts.
Canonical: 1h data uses 'datetime', 1d data may use 'date' or 'datetime'.
"""
import os
from typing import Optional
import pandas as pd


def load_ohlcv(path: str, date_col: str = None) -> pd.DataFrame:
    """
    Load OHLCV CSV with flexible date column (datetime or date).
    Returns DataFrame with DatetimeIndex.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Data not found: {path}")

    df = pd.read_csv(path)
    # Try common date column names
    for col in (date_col,) if date_col else ['datetime', 'date', 'timestamp']:
        if col and col in df.columns:
            df[col] = pd.to_datetime(df[col])
            df = df.set_index(col)
            return df
    # Fallback: first datetime-like column
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            df[col] = pd.to_datetime(df[col])
            df = df.set_index(col)
            return df
    raise ValueError(f"No date/datetime column found in {path}. Columns: {list(df.columns)}")


def find_funding_path(symbol: str) -> Optional[str]:
    """Try multiple funding file naming patterns (aligns with fetch_1h_data)."""
    base = symbol.replace('/', '_')
    for pattern in [
        f"data/funding_rates/{base}_funding.csv",
        f"data/funding_rates/{base}_USDT_funding.csv",
        f"data/funding_rates/{base}_USDT_USDT_funding.csv",
    ]:
        if os.path.exists(pattern):
            return pattern
    return None
