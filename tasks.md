# Crypto Bot Project Task List

This document tracks the development progress of the Crypto Bot strategies based on the `crypto-bot-playbook.md`.

## Status Legend
- [ ] Todo
- [ ] In Progress
- [x] Done
- [-] Skipped/Deferred

---

## Phase 1: Infrastructure & Setup (Day 1)
- [ ] **Environment Setup**
    - [ ] Create project directory `~/crypto-bot`.
    - [ ] Set up Python virtual environment (`venv`).
    - [ ] Install dependencies: `ccxt`, `freqtrade`, `vectorbt`, `pandas`, `numpy`, `ta-lib`, `python-telegram-bot`, `jupyter`, `hmmlearn`, `scikit-learn`, `matplotlib`.
    - [ ] Install `pandas-ta` (fallback if ta-lib fails).
    - [ ] Verify CCXT connection to Binance.
- [ ] **Project Structure**
    - [ ] Create directory structure:
        - `config/`
        - `data/ohlcv/`, `data/funding_rates/`, `data/unlocks/`
        - `strategies/`
        - `research/notebooks/`, `research/backtests/`, `research/walk_forward/`
        - `utils/`

## Phase 2: Strategy Development & Backtesting

### Strategy 1: Weekend Momentum Premium (Target: Week 1)
- [ ] **Data & Research**
    - [ ] Fetch 2+ years of daily OHLCV data for BTC, ETH, SOL, LINK.
    - [ ] Implement basic backtest in VectorBT (Fri close -> Mon close).
- [ ] **Refinement**
    - [ ] Implement Trend Filter version (EMA50 > EMA200).
    - [ ] Compare results (Sharpe, Drawdown) vs Buy & Hold.
- [ ] **Implementation**
    - [ ] Create `strategies/WeekendMomentum.py` for Freqtrade.
    - [ ] Implement `populate_indicators`, `populate_entry_trend`, `populate_exit_trend`.

### Strategy 2: Funding Rate Mean Reversion (Target: Week 1-2)
- [ ] **Data Collection**
    - [ ] Create `utils/data_collector.py` to fetch historical funding rates.
    - [ ] Fetch 2 years of funding data for BTC, ETH, SOL.
- [ ] **Research & Backtest**
    - [ ] Implement `backtest_funding_mean_reversion` logic.
    - [ ] Optimize entry/exit thresholds (default: >0.05% entry, <0.01% exit).
- [ ] **Implementation**
    - [ ] Create `strategies/FundingReversion.py`.
    - [ ] Implement `Live Signal Monitor` (`utils/telegram_alerts.py`) for real-time funding alerts.

### Strategy 3: Token Unlock Event Trading (Target: Week 2)
- [ ] **Data Source**
    - [ ] Create `strategies/UnlockTrader.py`.
    - [ ] Implement `get_upcoming_unlocks` (API or manual CSV).
    - [ ] Implement `score_unlock_impact` logic.
- [ ] **Backtest**
    - [ ] Implement `backtest_unlock_strategy` (Short 30d before, cover 14d after).
    - [ ] Validate against historical events.

### Strategy 4: Liquidation Cascade Bounce (Target: Week 2-3)
- [ ] **Detection System**
    - [ ] Implement `LiquidationMonitor` class in `utils/data_collector.py`.
    - [ ] Implement cascade detection logic (Funding flip, Price dump, OI drop).
- [ ] **Strategy Logic**
    - [ ] Create `strategies/CascadeBounce.py`.
    - [ ] Implement entry (first green 4hr candle), stop (2% below low), target (50% retracement).
- [ ] **Validation**
    - [ ] Backtest against known historical cascades (e.g., 2025-10-10, 2024-08-05).

### Strategy 5: Regime-Adaptive Grid Bot (Target: Week 3)
- [ ] **Regime Detection**
    - [ ] Implement `CryptoRegimeDetector` class using `hmmlearn`.
    - [ ] Train HMM on historical data to label Bull, Bear, Sideways, Transition.
- [ ] **Grid Implementation**
    - [ ] Create `strategies/RegimeGrid.py`.
    - [ ] Implement Grid logic (calculate levels, orders).
    - [ ] Integrate Regime Detector: Only active in 'Sideways' regime.

### Strategy 6: Cross-L2 DEX Arbitrage (Advanced - Optional)
- [ ] **Scanner**
    - [ ] Setup Web3 connections for Arbitrum, Base, Optimism.
    - [ ] Implement `CrossL2Scanner` to check Uniswap V3 quotes.
    - [ ] Implement spread calculation (including bridge/gas costs).

## Phase 3: Validation Pipeline
- [ ] **Phase 1: Historical Backtest**
    - [ ] Run Freqtrade backtest for all strategies.
    - [ ] Criteria: Sharpe > 1.0, Max DD < 20%, Win Rate > 55%.
- [ ] **Phase 2: Walk-Forward Analysis**
    - [ ] Implement `walk_forward_test` script in `research/walk_forward/`.
    - [ ] Run analysis (Train 6mo, Test 1mo).
- [ ] **Phase 3: Monte Carlo Validation**
    - [ ] Implement `monte_carlo_validation` script.
    - [ ] Run 1000 simulations per strategy.
    - [ ] Verify 5th percentile return is positive.

## Phase 4: Risk Management & Monitoring
- [ ] **Risk Manager**
    - [ ] Create `utils/risk_manager.py`.
    - [ ] Implement max risk per trade (1%), max daily loss (3%), max total drawdown (15%).
    - [ ] Implement position sizing logic.
- [ ] **Monitoring & Alerts**
    - [ ] Create `utils/daily_report.py` for Telegram.
    - [ ] specific alerts for Strategy 2 (Funding) and Strategy 4 (Cascades).

## Phase 5: LIVE Deployment
- [ ] **Paper Trading (Dry Run)**
    - [ ] Configure `config/config.json` for dry-run.
    - [ ] Run top performing strategy for 4-8 weeks.
    - [ ] Compare Paper results vs Backtest.
- [ ] **Live Micro-Deployment**
    - [ ] Configure `config/config.json` for live trading (Binance API).
    - [ ] Set conservative limits ($50/trade, max 3 trades).
    - [ ] Enable circuit breakers.

## Development Log & Notes
- **[Date]**: Initial task list created.
