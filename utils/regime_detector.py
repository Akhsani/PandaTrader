import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
import logging
import warnings

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
        Features for regime detection:
        1. Daily returns
        2. Rolling volatility (14d)
        3. Return momentum (7d cumulative return)
        """
        df = price_df.copy()
        
        # Ensure we have a 'close' column (case-insensitive check)
        if 'close' not in df.columns:
             # Try to find a column that looks like 'close'
             close_col = next((col for col in df.columns if col.lower() == 'close'), None)
             if close_col:
                 df['close'] = df[close_col]
             else:
                 raise ValueError("DataFrame must contain a 'close' or 'Close' column")

        # Convert to numeric, forcing errors to NaN
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df.dropna(subset=['close'], inplace=True)

        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=14).std()
        df['momentum'] = df['returns'].rolling(window=7).sum()
        
        # Drop NaN values created by returns and rolling windows
        df.dropna(inplace=True)
        
        if len(df) == 0:
             return np.array([]), df

        features = df[['returns', 'volatility', 'momentum']].values
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
            'returns': ['mean', 'std'],
            'volatility': 'mean'
        })
        
        # We need to flatten the MultiIndex columns if present or access strictly
        # Easier to just access by tuple keys if aggregations resulted in MultiIndex
        
        # Check if regime_stats has multiindex columns
        if isinstance(regime_stats.columns, pd.MultiIndex):
             mean_returns = regime_stats[('returns', 'mean')]
             mean_vol = regime_stats[('volatility', 'mean')]
        else:
             # Fallback if structure is different
             mean_returns = regime_stats['returns']['mean']
             mean_vol = regime_stats['volatility']['mean']
        
        # Sort regimes based on mean returns
        sorted_by_return = mean_returns.sort_values()
        regimes_sorted = sorted_by_return.index.tolist()
        
        # Assign Bear (lowest return) and Bull (highest return)
        bear_regime = regimes_sorted[0]
        bull_regime = regimes_sorted[-1]
        
        self.regime_labels = {
             bear_regime: 'BEAR',
             bull_regime: 'BULL'
        }
        
        # Identify Sideways and Transition from the remaining regimes
        remaining = [r for r in regimes_sorted if r not in [bear_regime, bull_regime]]
        
        if remaining:
            # Sort remaining by volatility (lowest volatility = Sideways)
            remaining_vols = mean_vol.loc[remaining].sort_values()
            sideways_regime = remaining_vols.index[0]
            self.regime_labels[sideways_regime] = 'SIDEWAYS'
            
            if len(remaining) > 1:
                # Any other remaining regimes are Transition
                for r in remaining_vols.index[1:]:
                     self.regime_labels[r] = 'TRANSITION'
        
        df['regime_label'] = df['regime'].map(self.regime_labels)
        
        # Debug logging
        # logger.info("Regime Mapping constructed:")
        # for r, label in self.regime_labels.items():
        #    logger.info(f"  Regime {r} -> {label}")
            
    def predict(self, price_df):
        """Predict regimes for new data (must be fitted first)"""
        if self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
            
        features, df = self.prepare_features(price_df)
        if len(features) == 0:
             return df # Empty or invalid

        states = self.model.predict(features)
        df['regime'] = states
        df['regime_label'] = df['regime'].map(self.regime_labels)
        return df

    def current_regime(self, recent_prices):
        """Detect current regime from recent price data"""
        if self.model is None:
            # logger.warning("Model not fitted. Returning UNKNOWN.")
            return 'UNKNOWN'
            
        features, _ = self.prepare_features(recent_prices)
        if len(features) < 1:
            return 'UNKNOWN'
        
        # Predict on the last available feature set
        # reshaping for single sample prediction
        last_feature = features[-1].reshape(1, -1)
        state = self.model.predict(last_feature)
        return self.regime_labels.get(state[0], 'UNKNOWN')
