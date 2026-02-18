"""
Cascade detection for S2 Signal Amplifier (Phase 2B.5).
Detects liquidation cascade conditions: RSI < 30 + volume spike + optional funding flip.
Used by FundingReversion to double conviction when cascade fires on BTC.
"""
import pandas as pd
import numpy as np


def detect_cascade(ohlcv_df: pd.DataFrame, funding_df: pd.DataFrame = None,
                   rsi_period: int = 14, vol_sma_period: int = 24,
                   vol_spike_mult: float = 1.5) -> pd.Series:
    """
    Detect cascade conditions: RSI < 30 + volume spike + (optional) funding flip.
    Returns boolean Series aligned with ohlcv_df index.
    """
    try:
        import talib
    except ImportError:
        # Fallback: simple RSI approximation
        delta = ohlcv_df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        rsi = rsi.fillna(50)
    else:
        rsi = talib.RSI(ohlcv_df['close'], timeperiod=rsi_period)
        rsi = pd.Series(rsi, index=ohlcv_df.index).fillna(50)

    vol_sma = ohlcv_df['volume'].rolling(vol_sma_period).mean()
    vol_spike = ohlcv_df['volume'] > (vol_spike_mult * vol_sma)

    oversold = rsi < 30
    cascade_base = oversold & vol_spike

    # Funding flip: funding rate crossed from positive to negative
    if funding_df is not None and not funding_df.empty and 'fundingRate' in funding_df.columns:
        funding = funding_df['fundingRate'].reindex(ohlcv_df.index, method='ffill')
        funding_prev = funding.shift(1)
        funding_flip = (funding_prev > 0) & (funding <= 0)
        cascade_base = cascade_base & funding_flip.fillna(False)
    elif funding_df is not None and not funding_df.empty:
        # Try common column names
        fr_col = [c for c in funding_df.columns if 'funding' in c.lower() or 'rate' in c.lower()]
        if fr_col:
            funding = funding_df[fr_col[0]].reindex(ohlcv_df.index, method='ffill')
            funding_prev = funding.shift(1)
            funding_flip = (funding_prev > 0) & (funding <= 0)
            cascade_base = cascade_base & funding_flip.fillna(False)

    return cascade_base.fillna(False)


def cascade_fires_now(df: pd.DataFrame, funding_df: pd.DataFrame = None) -> bool:
    """
    Check if cascade condition fires on the last row. For use in strategy callbacks.
    """
    if df is None or len(df) < 50:
        return False
    series = detect_cascade(df, funding_df)
    return bool(series.iloc[-1]) if len(series) > 0 else False
