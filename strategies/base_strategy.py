from freqtrade.strategy import IStrategy
from pandas import DataFrame
import logging
import sys
import os

# Add project root to path to allow importing utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.risk_manager import RiskManager
from utils.regime_detector import CryptoRegimeDetector

logger = logging.getLogger(__name__)

class BaseStrategy(IStrategy):
    """
    Base Strategy for PandaTrader.
    Implements centralized Risk Management and Regime Detection.
    """
    # Minimal ROI (Overridden by subclasses)
    minimal_roi = {"0": 100}
    stoploss = -0.05
    timeframe = '1h'
    
    # Risk Config (Should be loaded from config file in real app)
    risk_config = {
        'max_risk_per_trade': 0.01,
        'max_daily_loss': 0.03,
        'max_portfolio_drawdown': 0.15,
        'initial_capital': 1000.0
    }
    
    def __init__(self, config: dict) -> None:
        super().__init__(config)
        self.risk_manager = RiskManager(self.risk_config)
        self.regime_detector = CryptoRegimeDetector()
        self.is_regime_model_fitted = False
        
        logger.info(f"BaseStrategy Initialized. Risk Config: {self.risk_config}")

    def bot_start(self, **kwargs) -> None:
        """
        Called only once after bot instantiation.
        """
        pass

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time: str, entry_tag: str,
                            side: str, **kwargs) -> bool:
        """
        Freqtrade callback to confirm trade entry.
        We use this to enforce Risk Management and Regime Gating.
        """
        # 1. Risk Manager Check (Kill Switch, Daily Loss)
        if not self.risk_manager.check_trade_allowed(pair, self.__class__.__name__):
            logger.warning(f"Trade blocked by Risk Manager: {pair}")
            return False
            
        # 2. Regime Gating (Optional: Subclasses can override or we enforce here)
        # By default, we might block LONGs in BEAR regimes for all strategies?
        # Let's leave that logic to specific strategies for flexibility, 
        # but provide the data.
        
        return True

    def custom_stake_amount(self, pair: str, current_time: str, current_rate: float,
                            proposed_stake: float, min_stake: float, max_stake: float,
                            leverage: float, entry_tag: str, side: str,
                            **kwargs) -> float:
        """
        Calculate Position Size based on Risk Manager.
        """
        # Calculate stop loss price distance
        # Note: Freqtrade handles stoploss as %, but RiskManager expects price levels for precision
        # We'll estimate based on self.stoploss
        
        stop_distance_pct = abs(self.stoploss)
        stop_price = current_rate * (1 - stop_distance_pct) if side == 'long' else current_rate * (1 + stop_distance_pct)
        
        # Check for strategy-specific risk override
        strategy_risk = getattr(self, 'custom_risk_per_trade', None)
        
        # Risk Manager Sizing
        safe_amount = self.risk_manager.calculate_position_size(current_rate, stop_price, risk_per_trade=strategy_risk)
        
        # Convert to stake currency (e.g. USDT)
        stake = safe_amount * current_rate
        
        # Ensure within Freqtrade limits
        return min(stake, max_stake)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Common indicators (Regime Detection).
        Subclasses MUST call super().populate_indicators() or handle this logic.
        """
        # Train/Predict Regime
        # In a real live run, we'd need to persist the model or retrain periodically.
        # For simplicity here, we check if fitted.
        
        if not self.is_regime_model_fitted:
            # We need valid data to fit. 
            # Freqtrade often passes startup candles. 
            # We assume dataframe is large enough.
            if len(dataframe) > 200:
                self.regime_detector.fit(dataframe)
                self.is_regime_model_fitted = True
                logger.info("Regime Model Fitted")
        
        if self.is_regime_model_fitted:
             df_regime = self.regime_detector.predict(dataframe)
             dataframe['regime'] = df_regime['regime_label']
        else:
             dataframe['regime'] = 'UNKNOWN'
             
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe
