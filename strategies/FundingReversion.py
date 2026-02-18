# Strategies/FundingReversion.py
from pandas import DataFrame
import talib.abstract as ta
import pandas as pd
import numpy as np
import logging

from base_strategy import BaseStrategy

try:
    from utils.cascade_detector import cascade_fires_now
except ImportError:
    cascade_fires_now = lambda df, fd=None: False

logger = logging.getLogger(__name__)


try:
    from utils.funding_utils import z_to_risk as _z_to_risk
except ImportError:
    def _z_to_risk(z):
        return 0.005 if z is None else (0.015 if abs(z) >= 2.5 else (0.01 if abs(z) >= 2.0 else 0.005))


class FundingReversion(BaseStrategy):
    """
    Funding Rate Mean Reversion Strategy
    
    Hypothesis: 
    When funding rates hit extremes (>0.05% or <-0.05%), they mean-revert.
    - Extreme Positive Funding -> Short
    - Extreme Negative Funding -> Long
    
    Note: Requires funding rate data. Freqtrade support for funding rates in backtesting 
    depends on data availability and configuration. This strategy assumes 'funding_rate' 
    column is available in dataframe (custom data or future support).
    """
    INTERFACE_VERSION = 3
    timeframe = '1h' # Using 1h to capture funding moves better than 1d
    can_short = True
    
    # Risk settings (Strategy specific overrides)
    stoploss = -0.05
    custom_risk_per_trade = 0.0025  # Base; overridden by dynamic Z-based sizing
    
    # Strategy parameters (reoptimized 2026-02-18: strategy2_params.json)
    buy_params = {
        "z_score_threshold": 1.5,
        "adx_threshold": 20
    }
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Base Strategy Indicators (Regime Detection)
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # 2. Funding Rates (simulated for backtest if not Present)
        # In Freqtrade live, this comes from data provider.
        if 'funding_rate' not in dataframe.columns:
            dataframe['funding_rate'] = 0.0 # Placeholder
            
        # Z-Score of Funding Rate (Rolling 24h)
        dataframe['funding_mean'] = dataframe['funding_rate'].rolling(24).mean()
        dataframe['funding_std'] = dataframe['funding_rate'].rolling(24).std()
        dataframe['funding_zscore'] = (dataframe['funding_rate'] - dataframe['funding_mean']) / dataframe['funding_std']
        
        # ADX for Trend Filtering
        dataframe['adx'] = ta.ADX(dataframe, timeperiod=14)
        
        # Store last funding zscore for dynamic position sizing (Phase 2B.3)
        if len(dataframe) > 0 and 'funding_zscore' in dataframe.columns:
            self._last_funding_zscore = dataframe['funding_zscore'].iloc[-1]
        else:
            self._last_funding_zscore = 0.0
        
        # Store last df for cascade detection (Phase 2B.5)
        self._last_df = dataframe.copy() if len(dataframe) > 0 else None
        
        return dataframe

    def custom_stake_amount(self, pair: str, current_time: str, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: str, side: str,
                            **kwargs) -> float:
        """
        Dynamic position sizing (Phase 2B.3): Z=1.5->0.5%, Z=2.0->1.0%, Z=2.5+->1.5%.
        Drawdown throttle: >10% halve size, >15% zero until recovers to 8%.
        """
        # 1. Drawdown throttle (Phase 2B.3)
        rm = self.risk_manager
        if rm.peak_capital > 0:
            drawdown = (rm.peak_capital - rm.current_capital) / rm.peak_capital
            if drawdown >= 0.15:
                logger.warning(f"Drawdown throttle: {drawdown:.1%} >= 15%, blocking new position")
                return min_stake
            throttle_mult = 0.5 if drawdown >= 0.10 else 1.0
        else:
            throttle_mult = 1.0
        
        # 2. Z-based risk (Phase 2B.3)
        z = getattr(self, '_last_funding_zscore', 1.5)
        risk_pct = _z_to_risk(z)
        
        stop_distance_pct = abs(self.stoploss)
        stop_price = current_rate * (1 - stop_distance_pct) if side == 'long' else current_rate * (1 + stop_distance_pct)
        
        safe_amount = rm.calculate_position_size(current_rate, stop_price, risk_per_trade=risk_pct)
        stake = safe_amount * current_rate * throttle_mult
        
        # Cascade amplifier (Phase 2B.5): boost stake when cascade fires.
        # Phase 3A: 2x caused DD > 25%; reduced to 1.5x. Set to 1.0 to disable.
        CASCADE_AMPLIFIER = 1.5
        if CASCADE_AMPLIFIER > 1.0 and getattr(self, '_last_df', None) is not None and len(self._last_df) > 50:
            if cascade_fires_now(self._last_df, None):
                stake *= CASCADE_AMPLIFIER
                logger.info(f"Cascade amplifier: {CASCADE_AMPLIFIER}x stake for {pair}")
        
        return min(max(stake, min_stake), max_stake)

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Entry Logic with Regime Gating
        """
        
        # LONG Entry:
        # 1. Funding is extremely negative (Short Squeeze potential)
        # 2. Market is NOT in 'BEAR' regime (Master Switch)
        # 3. ADX is low (Mean Reversion works best in chop)
        
        dataframe.loc[
            (dataframe['funding_zscore'] < -self.buy_params['z_score_threshold']) &
            (dataframe['regime'] != 'BEAR') &  # <--- REGIME MASTER SWITCH
            (dataframe['adx'] < self.buy_params['adx_threshold']) &
            (dataframe['volume'] > 0),
            'enter_long'] = 1
            
        # SHORT Entry:
        # 1. Funding is extremely positive (Long Squeeze potential)
        # 2. Market is NOT in 'BULL' regime? (Optional, maybe we allow shorts in Bull if funding is crazy)
        # Let's be safe: Don't short in Strong Bull.
        
        dataframe.loc[
            (dataframe['funding_zscore'] > self.buy_params['z_score_threshold']) &
            (dataframe['regime'] != 'BULL') & 
            (dataframe['adx'] < self.buy_params['adx_threshold']) &
            (dataframe['volume'] > 0),
            'enter_short'] = 1
            
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit Long: Funding normalizes (Z-Score > -0.5)
        dataframe.loc[
            (dataframe['funding_zscore'] > -0.5) &
            (dataframe['volume'] > 0),
            'exit_long'] = 1
            
        # Exit Short: Funding normalizes (Z-Score < 0.5)
        dataframe.loc[
            (dataframe['funding_zscore'] < 0.5) &
            (dataframe['volume'] > 0),
            'exit_short'] = 1
            
        return dataframe
