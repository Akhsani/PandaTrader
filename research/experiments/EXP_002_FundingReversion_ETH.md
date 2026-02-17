# EXP_002: Funding Rate Mean Reversion (ETH/USDT)

## 1. Hypothesis
**Observation:** Perpetual futures funding rates periodically hit extremes, indicating crowded positioning.
**Hypothesis:** Price tends to revert when funding rates are extreme (>0.05% or <-0.05%), as positions unwind or are squeezed.
**Assumptions:** Funding rate data from Binance is a reliable proxy for market sentiment. 1-hour candles are granular enough to capture the reversion.

## 2. Methodology
- **Strategy Code**: `strategies/FundingReversion.py`
- **Data**: ETH/USDT (Binance Futures), 1h OHLCV + Funding Rates, 2024-02 to 2026-02.
- **Parameters**: 
    - `z_score_threshold`: Entry trigger (Z-Score of funding rate).
    - `adx_threshold`: Trend filter (ADX < threshold).
    - `stop_loss`: Fixed percentage stop.

## 3. Results

### A. Initial Backtest
- **Period**: 2024-02-18 to 2026-02-17
- **Total Return**: +31.54% (ETH), -3.55% (SOL)
- **Finding**: Simple thresholds were insufficient; added Z-Score and ADX filters.

### B. Walk-Forward Analysis (Robustness)
- **Train Window**: 180 days | **Test Window**: 30 days
- **Asset**: ETH/USDT
- **Total Return (Out-of-Sample)**: **+20.47%**
- **Win Rate**: **58.85%**
- **Trades**: 226
- **Optimized Parameters**:
    - `z_score_threshold`: **1.5**
    - `adx_threshold`: **30**
    - `stop_loss`: **0.05**

### C. Monte Carlo Validation (Stress Test)
- **Simulations**: 1000
- **Median Final Equity**: **$1252.48** (+25.2%)
- **Risk Analysis**:
    - **Probability of Loss**: 29.30%
    - **Probability of Drawdown > 20%**: **86.40%** (High)
    - **Worst Case Drawdown**: -71.23%

## 4. Conclusion
**STATUS: APPROVED WITH CAUTION**
The strategy has a verified statistical edge on ETH/USDT. However, the high probability of significant drawdowns (86% chance of >20% DD) implies substantial volatility risk.

## 5. Next Steps
1.  **Deployment**: Valid for live trading on ETH/USDT.
2.  **Risk Management**: Strict position sizing (0.5% - 1% risk per trade) is mandatory.
3.  **Monitoring**: Use `utils/telegram_alerts.py` to monitor live signals matched against the Z=1.5 threshold.
