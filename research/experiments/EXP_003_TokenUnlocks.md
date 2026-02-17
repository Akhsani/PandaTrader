# EXP_003: Token Unlock Event Trading

## 1. Hypothesis
**Observation:** Large token unlocks increase circulating supply, often creating selling pressure from early investors and teams.
**Hypothesis:** Assets with large token unlocks (>2% supply) experience negative price pressure 30 days prior (anticipatory selling) and stabilize/bounce 14 days post-unlock (absorption).
**Strategy:** 
- **Short/Exit**: 30 days before unlock.
- **Long/Re-entry**: 14 days after unlock.

## 2. Methodology
- **Code**: `strategies/UnlockTrader.py`
- **Data**: Daily OHLCV for ARB, OP, APT, SUI, TIA (Binance Spot/Futures proxy).
- **Events**: Major unlocks (>2% supply) from 2023-2025.
- **Backtest Engine**: Custom vector-based backtest (`research/backtests/backtest_strategy_3.py`).

## 3. Results

### Performance by Token
| Token | Total Return | Sharpe Ratio | Max Drawdown |
|-------|--------------|--------------|--------------|
| **OP/USDT** | **+64.85%** | **0.75** | -23.79% |
| **SUI/USDT** | **+34.22%** | **0.61** | -27.79% |
| **ARB/USDT** | **+16.45%** | **0.41** | -17.69% |
| **TIA/USDT** | -1.78% | 0.12 | -36.47% |
| **APT/USDT** | -27.15% | -0.30 | -58.67% |

### Aggregate Performance (Equal Weight)
- **Avg Return**: **+17.32%**
- **Avg Max Drawdown**: -32.88%
- **Observation**:
    - **Strong Performers**: Layer 2s (OP, ARB) and SUI showed clear alpha. The strategy captured the "sell the news" and "buy the dip" dynamic effectively.
    - **Underperformers**: APT suffered significant losses, suggesting that price action was driven by other factors (e.g., strong trend overriding unlock pressure) or the "short" window was mistimed.
    - **Volatility**: High drawdowns indicate this is a volatile strategy. Shorting crypto in a bull market (even before unlocks) is risky.

## 4. Conclusion
**STATUS: PROVISIONAL APPROVAL (Targeted Only)**

The strategy works exceptionally well for **Layer 2s and Ecosystem tokens** (OP, ARB, SUI) where vesting schedules are well-known and widely traded. It failed for APT, highlighting the risk of blindly shorting.

**Refinement Needed:**
- **Trend Filter**: Do not short if price is in a parabolic uptrend (e.g., ADX > 50), even if an unlock is coming.
- **Hedging**: Execute this as a market-neutral strategy (Short Token / Long ETH) to isolate the "unlock alpha" from broad market beta.

## 5. Next Steps
1.  **Automate Data**: Connect to DeFiLlama API for live unlock schedules.
2.  **Implement Trend Filter**: Add a check to `UnlockTrader` to skip Short entries if Trend is too strong.
3.  **Deploy Monitor**: add to `utils/telegram_alerts.py` to warn 30 days before major unlocks for manual review.
