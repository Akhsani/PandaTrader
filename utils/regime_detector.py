import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import logging
import warnings
import talib.abstract as ta

# Suppress warnings from hmmlearn/sklearn if needed
warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoRegimeDetector:
    def __init__(self, n_regimes=4, random_state=42):
        self.n_regimes = n_regimes
        self.random_state = random_state
        self.model = None
        self.regime_labels = {}

    def prepare_features(self, price_df):
        """
        Features for regime detection (v2 - Improved):
        1. Log Returns (Statistical stability)
        2. Rolling Volatility (14d) - Derived from Log Returns
        3. ADX (Trend Strength) - Distinguishes Sideways vs Trend
        4. RSI (Momentum/Overbought) - Helpful for distinguishing Bull vs Bear
        """
        df = price_df.copy()
        
        # Ensure we have required columns for TA-Lib logic (open, high, low, close)
        # normalize column names to lowercase
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        # check if all present, if not, try to map or error
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
             # Try to be flexible if only close is available (but ADX needs High/Low)
             if 'adx' in str(missing):
                  logger.warning(f"Missing columns for ADX: {missing}. Falling back to limited features.")
        
        # 1. Log Returns
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        
        # 2. Volatility (from log returns)
        df['volatility'] = df['log_ret'].rolling(window=14).std()
        
        # 3. ADX (Trend Strength)
        try:
            df['adx'] = ta.ADX(df, timeperiod=14)
        except Exception as e:
            logger.warning(f"Could not calculate ADX: {e}. Using proxy.")
            df['adx'] = 0 # Placeholder if fails
            
        # 4. RSI (Additional Momentum)
        try:
            df['rsi'] = ta.RSI(df, timeperiod=14)
        except:
             df['rsi'] = 50
        
        # Drop NaN values created by indicators
        df.dropna(inplace=True)
        
        # Scale/Normalize features? 
        # GaussianHMM assumes Gaussian distribution. 
        # ADX is 0-100, RSI is 0-100, LogRet is small float. 
        # Ideally we should standardize. But for now let's pass raw and let HMM handle means/vars.
        # Actually, standardization is highly recommended for fitting.
        
        if len(df) == 0:
             return np.array([]), df

        # We use ADX, Volatility, and RSI? or LogRet?
        # Research says: Volatility + Trend Strength are best for regimes.
        features = df[['log_ret', 'volatility', 'adx']].values
        return features, df

    def fit(self, price_df):
        """Train HMM on historical data"""
        if len(price_df) < 100:
            logger.warning("Insufficient data to train HMM. Need at least 100 data points.")
            return None

        features, df = self.prepare_features(price_df)
        
        if len(features) == 0:
             logger.warning("No features could be generated from data.")
             return None

        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=100,
            tol=0.01,
            random_state=self.random_state
        )
        self.model.fit(features)
        
        # Decode states
        states = self.model.predict(features)
        df['regime'] = states
        
        # Label regimes by characteristics
        self._label_regimes(df)
        
        return df

    def _label_regimes(self, df):
        """Assign human-readable labels to regimes based on their stats"""
        regime_stats = df.groupby('regime').agg({
            'log_ret': ['mean'],
            'volatility': ['mean'],
            'adx': ['mean']
        })
        
        # Flatten columns
        if isinstance(regime_stats.columns, pd.MultiIndex):
             mean_ret = regime_stats[('log_ret', 'mean')]
             mean_vol = regime_stats[('volatility', 'mean')]
             mean_adx = regime_stats[('adx', 'mean')]
        else:
             mean_ret = regime_stats['log_ret']['mean']
             mean_vol = regime_stats['volatility']['mean']
             mean_adx = regime_stats['adx']['mean']
        
        # Sort regimes
        regimes = mean_ret.index.tolist()
        
        # 1. Bull vs Bear: Highest vs Lowest Return
        sorted_by_ret = mean_ret.sort_values()
        bear_regime = sorted_by_ret.index[0]
        bull_regime = sorted_by_ret.index[-1]
        
        self.regime_labels = {
            bear_regime: 'BEAR',
            bull_regime: 'BULL'
        }
        
        remaining = [r for r in regimes if r not in [bear_regime, bull_regime]]
        
        if remaining:
            # 2. Sideways vs Transition:
            # Sideways should have Low ADX (No Trend) and Low/Med Volatility
            # Transition might have High Volatility or Med ADX
            
            # Use ADX to distinguish
            sorted_by_adx = mean_adx.loc[remaining].sort_values()
            sideways_regime = sorted_by_adx.index[0] # Lowest ADX
            self.regime_labels[sideways_regime] = 'SIDEWAYS'
            
            if len(remaining) > 1:
                # The last one is Transition
                for r in sorted_by_adx.index[1:]:
                     self.regime_labels[r] = 'TRANSITION'
        
        df['regime_label'] = df['regime'].map(self.regime_labels)
            
    def predict(self, price_df):
        """Predict regimes for new data (must be fitted first)"""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features, df = self.prepare_features(price_df)
        if len(features) == 0:
             return df 

        states = self.model.predict(features)
        df['regime'] = states
        df['regime_label'] = df['regime'].map(self.regime_labels)
        return df

    def current_regime(self, recent_prices):
        """Detect current regime from recent price data"""
        if self.model is None:
            return 'UNKNOWN'
            
        features, _ = self.prepare_features(recent_prices)
        if len(features) < 1:
            return 'UNKNOWN'
        
        last_feature = features[-1].reshape(1, -1)
        state = self.model.predict(last_feature)
        return self.regime_labels.get(state[0], 'UNKNOWN')
