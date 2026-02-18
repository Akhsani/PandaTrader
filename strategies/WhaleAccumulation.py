"""
Strategy 8: On-Chain Whale Accumulation Tracker
Long when Smart Money net inflow > threshold. Regime filter: BULL/SIDEWAYS preferred.
Uses Nansen API when available; falls back to synthetic momentum proxy in backtest.
"""
from pandas import DataFrame
import pandas as pd
import numpy as np
import logging
import sys
import os

for p in ['/freqtrade', os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))]:
    if p not in sys.path:
        sys.path.insert(0, p)

from strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

try:
    from utils.nansen_whale_tracker import NansenWhaleTracker, TOKEN_MAP, SYMBOL_TO_PAIR
except ImportError:
    NansenWhaleTracker = None
    TOKEN_MAP = {}
    SYMBOL_TO_PAIR = {'BTC': 'BTC/USDT', 'ETH': 'ETH/USDT', 'SOL': 'SOL/USDT'}


def compute_synthetic_signal(dataframe: DataFrame, lookback: int = 7, vol_mult: float = 1.2) -> pd.Series:
    """Synthetic accumulation proxy from OHLCV when Nansen unavailable."""
    ret = dataframe['close'].pct_change(lookback)
    vol_ma = dataframe['volume'].rolling(20).mean().replace(0, np.nan)
    vol_spike = (dataframe['volume'] / vol_ma) > vol_mult
    return ((ret > 0) & vol_spike).astype(int)


class WhaleAccumulation(BaseStrategy):
    """
    Whale Accumulation: Long when Smart Money accumulates.
    Active in BULL and SIDEWAYS; reduced in BEAR/TRANSITION.
    """
    INTERFACE_VERSION = 3
    timeframe = '1d'
    can_short = False

    stoploss = -0.05
    custom_risk_per_trade = 0.01

    buy_params = {
        "accumulation_threshold": 0.3,  # WFA-optimized (0.5 underperforms)
        "lookback": 7,
    }

    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self._tracker = NansenWhaleTracker() if NansenWhaleTracker else None
        self._cached_scores = {}
        self._cache_time = None
        self._cache_ttl_sec = 3600  # Refresh hourly

    def _get_accumulation_score(self, pair: str) -> float:
        """Get cached accumulation score for pair. Returns 0 if unavailable."""
        if self._tracker and self._tracker.api_key:
            import time
            symbol = pair.replace('/USDT', '').replace('/BUSD', '') if pair else ''
            now = time.time()
            if self._cache_time and (now - self._cache_time) < self._cache_ttl_sec and symbol in self._cached_scores:
                return self._cached_scores.get(symbol, 0)
            scores = self._tracker.get_accumulation_scores(
                symbols=[symbol] if symbol else list(SYMBOL_TO_PAIR.keys()),
                threshold=self.buy_params.get('accumulation_threshold', 0.5),
            )
            self._cached_scores = {sym: s['score'] for sym, s in scores.items()}
            self._cache_time = now
            return self._cached_scores.get(symbol, 0)
        return 0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe = super().populate_indicators(dataframe, metadata)

        pair = metadata.get('pair', '')
        if not pair:
            return dataframe

        score = self._get_accumulation_score(pair)
        if score > 0:
            dataframe['accumulation_score'] = score
        else:
            lookback = self.buy_params.get('lookback', 7)
            signal = compute_synthetic_signal(dataframe, lookback=lookback)
            dataframe['accumulation_score'] = signal.astype(float)

        threshold = self.buy_params.get('accumulation_threshold', 0.5)
        dataframe['accumulation_signal'] = (dataframe['accumulation_score'] >= threshold).astype(int)

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        regime_ok = (dataframe['regime'] == 'BULL') | (dataframe['regime'] == 'SIDEWAYS')
        dataframe.loc[
            regime_ok &
            (dataframe['accumulation_signal'] == 1) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when signal flips or after hold period (handled by ROI/stoploss)
        dataframe.loc[
            (dataframe['accumulation_signal'] == 0) &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
        return dataframe
