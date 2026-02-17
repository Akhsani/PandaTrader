# Experiment 005: Regime-Adaptive Grid Bot

## Hypothesis
A Grid Bot performs best in sideways markets but suffers heavy drawdowns in trends. By using a Hidden Markov Model (HMM) to detect market regimes (Bull, Bear, Sideways, Transition), we can restrict grid trading to only "Sideways" regimes, thereby avoiding losses during strong trends.

## Methodology
- **Model**: Gaussian HMM with 4 components.
- **Features**: Daily Returns, 14-day Volatility, 7-day Momentum.
- **Training**: Trained on first 50% of 2-year BTC/USDT daily data.
- **Testing**: Tested on subsequent 50% (Out-of-Sample).
- **Strategy Logic**:
    - **SIDEWAYS**: Active Grid (Buy -1%, Sell +1%).
    - **BEAR**: Exit all positions (Cash preservation).
    - **BULL/TRANSITION**: No action (for this specific experiment).

## Results (BTC/USDT Daily)
- **Period**: ~1 year (Test Set)
- **Market Condition**: Bearish/Downtrend (Buy & Hold: -28.90%)

| Metric | Buy & Hold | Regime Grid Strategy |
| :--- | :--- | :--- |
| **Total Return** | -28.90% | **-11.18%** |
| **Trades** | 1 | 164 |
| **Relative Performance** | Baseline | **+17.72%** (vs Baseline) |

## Analysis
- **Defensive Strength**: The strategy successfully reduced losses by exiting/staying out during Bear regimes.
- **Active Hedging**: The grid logic likely generated small profits during lower-volatility periods while the overall market trended down.
- **Regime Detection**: The HMM successfully identified regimes distinct enough to provide a protective edge.
- **Limitations**:
    - Failed to generate *absolute* positive returns in a bear market (requires a Short strategy for Bear regime).
    - HMM convergence warning suggests data quantity (365 days) might be insufficient for robust training.

## Conclusion
- **Status**: **Promising / Defensive**.
- **Recommendation**:
    - The "Sideways" detection works for capital preservation.
    - To achieve positive returns, the "Bear" regime should trigger a Short strategy (or Short Grid) rather than just moving to cash.
    - Proceed to integrate into main bot as a "Safety Module" to disable long-only strategies during Bear regimes.
