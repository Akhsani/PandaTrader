import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from sklearn.preprocessing import StandardScaler
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
        self.scaler = StandardScaler()
        self.regime_labels = {}

    def prepare_features(self, price_df, fit_scaler=False):
        """
        Features for regime detection (v3 - Standardized & Trend Aware):
        1. Log Returns (Statistical stability)
        2. Rolling Volatility (14d)
        3. ADX (Trend Strength) - Distinguishes Sideways vs Trend
        4. Trend Position (Close / SMA200) - Distinguishes Highs from Lows
        """
        df = price_df.copy()
        
        # Ensure we have required columns
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
             if 'adx' in str(missing):
                  logger.warning(f"Missing columns for ADX: {missing}.")
        
        # 1. Log Returns
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        
        # 2. Volatility (from log returns)
        df['volatility'] = df['log_ret'].rolling(window=14).std()
        
        # 3. ADX (Trend Strength)
        try:
            df['adx'] = ta.ADX(df, timeperiod=14)
        except Exception as e:
            logger.warning(f"Could not calculate ADX: {e}. Using proxy.")
            df['adx'] = 0 
            
        # 4. Trend Position (Ratio to SMA200)
        # Helps distinguish "Volatile Bull (ATH)" from "Volatile Bear (Crash)"
        try:
            sma200 = ta.SMA(df, timeperiod=200)
            df['trend_pos'] = df['close'] / sma200
        except:
            df['trend_pos'] = 1.0
            
        # Drop NaN values created by indicators
        df.dropna(inplace=True)
        
        if len(df) == 0:
             return np.array([]), df

        # Select features
        feature_cols = ['log_ret', 'volatility', 'adx', 'trend_pos']
        raw_features = df[feature_cols].values
        
        # Standardize Features (Critical for HMM)
        if fit_scaler:
            self.scaler.fit(raw_features)
            
        scaled_features = self.scaler.transform(raw_features)
        
        return scaled_features, df

    def fit(self, price_df):
        """Train HMM on historical data"""
        if len(price_df) < 200: # Increased requirement for SMA200
            logger.warning("Insufficient data to train HMM. Need at least 200 data points.")
            return None

        # Prepare and Fit Scaler
        features, df = self.prepare_features(price_df, fit_scaler=True)
        
        if len(features) == 0:
             logger.warning("No features could be generated from data.")
             return None

        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type="full",
            n_iter=1000, # More iterations for convergence
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
            'trend_pos': ['mean']
        })
        
        # Flatten columns
        if isinstance(regime_stats.columns, pd.MultiIndex):
             mean_ret = regime_stats[('log_ret', 'mean')]
             mean_vol = regime_stats[('volatility', 'mean')]
             mean_trend = regime_stats[('trend_pos', 'mean')]
        else:
             mean_ret = regime_stats['log_ret']['mean']
             mean_vol = regime_stats['volatility']['mean']
             mean_trend = regime_stats['trend_pos']['mean']
        
        # Sorting Logic (Improved):
        # 1. Bear = Lowest Returns AND Low Trend Position
        # 2. Bull = Highest Returns OR High Trend Position
        
        regimes = mean_ret.index.tolist()
        
        # Sort by returns
        sorted_by_ret = mean_ret.sort_values()
        
        # Bear is generally lowest return
        bear_regime = sorted_by_ret.index[0]
        
        # Bull is generally highest return
        bull_regime = sorted_by_ret.index[-1]
        
        self.regime_labels = {
            bear_regime: 'BEAR',
            bull_regime: 'BULL'
        }
        
        remaining = [r for r in regimes if r not in [bear_regime, bull_regime]]
        
        if remaining:
            # Distinguish Sideways from Transition/Crash using Volatility
            sorted_by_vol = mean_vol.loc[remaining].sort_values()
            sideways_regime = sorted_by_vol.index[0] # Lowest Volatility
            self.regime_labels[sideways_regime] = 'SIDEWAYS'
            
            if len(remaining) > 1:
                # Any other remaining regimes are Transition
                for r in sorted_by_vol.index[1:]:
                     self.regime_labels[r] = 'TRANSITION'
        
        df['regime_label'] = df['regime'].map(self.regime_labels)
            
    def predict(self, price_df):
        """Predict regimes for new data (must be fitted first)"""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        # Don't refit scaler, just transform
        features, df = self.prepare_features(price_df, fit_scaler=False)
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
            
        features, _ = self.prepare_features(recent_prices, fit_scaler=False)
        if len(features) < 1:
            return 'UNKNOWN'
        
        last_feature = features[-1].reshape(1, -1)
        state = self.model.predict(last_feature)
        return self.regime_labels.get(state[0], 'UNKNOWN')
