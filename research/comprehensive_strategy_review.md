# Comprehensive Strategy Review: Strategies 1-5

## Executive Summary
This document consolidates the research, development, and validation of the first 5 strategies in the PandaTrader portfolio.
**Goal**: Build a diversified portfolio of uncorrelated strategies to perform in all market conditions.

### Portfolio Composition
| Role | Strategy | Status | Key Characteristic |
| :--- | :--- | :--- | :--- |
| **Striker (Bull)** | #1 Weekend Momentum | ✅ Approved | High Win Rate (77%), Low Frequency (Weekly). Exploits retail FOMO. |
| **Midfield (Any)** | #2 Funding Reversion | ⚠️ Caution | High Yield, High Risk (Hourly). Exploits over-leverage. |
| **Specialist (Event)** | #3 Token Unlocks | ✅ Provisional | Short-term Alpha on specific tokens (L2s). |
| **Defender (Crash)** | #4 Liquidation Bounce | ⏸️ Hold | Too rare. Misses V-bottoms due to safety filters. |
| **Goalkeeper (Bear)** | #5 Regime Grid | ✅ Approved | **Capital Preservation**. -3.7% loss in -30% Bear Market. |

---

## Strategy 1: Weekend Momentum Premium
**"The Striker"**
- **Hypothesis**: Crypto markets skew positive on weekends due to retail dominance/lower liquidity.
- **Logic**: Enter Long Friday Close -> Exit Monday Close. **Filter**: Trend (EMA50 > EMA200).
- **Asset**: BTC, ETH.
- **Parameters**:
    - `ma_fast`: 20
    - `ma_slow`: 50
    - `stop_loss`: 5%
- **Performance (BTC WFA)**:
    - **Return**: +20.84%
    - **Win Rate**: 77.78%
    - **Max DD**: -27%
- **Verdict**: **APPROVED**. Excellent satellite strategy. Low maintenance.

---

## Strategy 2: Funding Rate Mean Reversion
**"The Aggressive Midfielder"**
- **Hypothesis**: Extreme funding rates (>0.05%) signal overcrowded trades that will mean-revert.
- **Logic**: Long when Funding < -0.05%. Short when Funding > +0.05%. **Filter**: ADX < 30 (Avoid strong trends).
- **Asset**: ETH, SOL.
- **Parameters**:
    - `z_score_threshold`: 1.5
    - `adx_threshold`: 30
    - `stop_loss`: 5%
- **Performance (ETH WFA)**:
    - **Return**: +20.47%
    - **Win Rate**: 58.85%
    - **Max DD**: High (>20%)
- **Verdict**: **APPROVED WITH CAUTION**. High variance. Must use strict position sizing (0.5% risk).

---

## Strategy 3: Token Unlock Event Trading
**"The Event Specialist"**
- **Hypothesis**: Tokens drop before major unlocks (>2% supply) and stabilize after.
- **Logic**: Short 30 days prior. Cover/Long 14 days post.
- **Asset**: L2s (ARB, OP), New Ecosystems (SUI, APT).
- **Parameters**:
    - `unlock_threshold`: >2% Supply
    - `entry_window`: -30 days
- **Performance**:
    - **OP/USDT**: +64.85%
    - **SUI/USDT**: +34.22%
    - **APT/USDT**: -27.15% (Failed)
- **Verdict**: **PROVISIONAL**. Works great on "Vesting Heavy" tokens (L2s). Do not use on stronger trends (e.g., APT during rally).

---

## Strategy 4: Liquidation Cascade Bounce
**"The Benchwarmer"**
- **Hypothesis**: Buy the dip after massive liquidations flush out leverage.
- **Logic**: Wait for RSI < 30 + Vol Spike + funding flip. **Filter**: EMA200 uptrend.
- **Effectiveness**:
    - **ETH**: +3.8% (Profitable).
    - **BTC/SOL**: Flat/Loss.
- **Verdict**: **HOLD / LOW PRIORITY**. Filters made it too safe/rare. Missed the best "V-shape" reversals because relying on "Uptrend" filter during a crash is contradictory.

---

## Strategy 5: Regime-Adaptive Grid (HMM)
**"The Goalkeeper"**
- **Hypothesis**: Grid bots profit in sideways/chop but die in trends. Use HMM to detect "Sideways" and enable grid only then.
- **Logic**: 
    - **Detector**: HMM with features [Log Returns, Volatility, ADX].
    - **Action**: If Sideways -> Grid (Buy -0.5%, Sell +0.5%). If Bear/Bull -> Cash.
- **Performance (Bear Market Test)**:
    - **Buy & Hold**: -29.70%
    - **Strategy**: **-3.70%**
- **Verdict**: **APPROVED (DEFENSIVE)**. The ultimate portfolio stabilizer. It won't make you rich in a bull run (it sits out), but it saves you in a bear market.

---

## Master Comparison Table

| Strategy | Role | Edge Source | Risk Profile | Maintenance |
| :--- | :--- | :--- | :--- | :--- |
| **Weekend Momentum** | Profit Gen | Behavior (Retail) | Low | Low (Weekly) |
| **Funding Reversion** | Profit Gen | Structural (Perms) | High | Medium (Hourly) |
| **Token Unlocks** | Alpha | Tokenomics | Med-High | Low (Monthly) |
| **Liquidation** | Safety | Micro-Structure | Low | High (Real-time) |
| **Regime Grid** | Defense | Math (HMM) | Very Low | Med (Daily) |

## Deployment Plan
To run a balanced "PandaTrader" portfolio:
1.  **Core (50% Capital)**: **Strategy 5 (Regime Grid)**. Keeps capital safe, grinds profit in chop.
2.  **Growth (30% Capital)**: **Strategy 1 (Weekend)** + **Strategy 2 (Funding)**. The engines of return.
3.  **Alpha (20% Capital)**: **Strategy 3 (Unlocks)**. Opportunistic bets on specific tokens.
