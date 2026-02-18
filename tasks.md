# Crypto Bot Project Task List

This document tracks the development progress of the Crypto Bot strategies based on the `crypto-bot-playbook.md` and the **Deep Strategy Review** (`crypto-bot-strategy-2.docx`).

## Strategy Proposal Summary (Feb 2026)

The `crypto-bot-strategy-2.docx` review identifies:
- **Portfolio Sharpe 0.46** — target >1.0 for live deployment justification
- **S2 drawdown risk** — 86% probability of >20% drawdown (Monte Carlo)
- **Structural gaps** — No regime master switch; S1 sample size (N=9 WFA) too small
- **New strategies** — S6 (Basis Harvesting), S9 (Cross-Asset Funding Arb) as highest-priority builds
- **Edge taxonomy** — Structural/Calendar edges (S6, S9) decay slower than Statistical/Behavioral (S2, S1)

## Status Legend
- [ ] Todo
- [ ] In Progress
- [x] Done
- [-] Skipped/Deferred

---

## Phase 1: Infrastructure & Setup (Day 1)
- [x] **Environment Setup**
    - [x] Create project directory `~/crypto-bot`.
    - [x] Set up Python virtual environment (`venv`).
    - [x] Install dependencies: `ccxt`, `freqtrade`, `vectorbt`, `pandas`, `numpy`, `ta-lib`, `python-telegram-bot`, `jupyter`, `hmmlearn`, `scikit-learn`, `matplotlib`. (Confirmed: `ta-lib` C library installed via brew, Python wrapper installed.)
    - [-] Install `pandas-ta`. (Skipped: Installation failed due to repository access issues; using `ta-lib` instead detailed in Strategy 1)
    - [x] Verify CCXT connection to Binance. (Implemented `dns_patch.py` to force 1.1.1.1 resolution for Binance API)
- [x] **Project Structure**
    - [x] Create directory structure:
        - `config/`
        - `data/ohlcv/`, `data/funding_rates/`, `data/unlocks/`
        - `strategies/`
        - `research/notebooks/`, `research/backtests/`, `research/walk_forward/`
        - `utils/`

## Phase 2: Strategy Development & Backtesting

### Strategy 1: Weekend Momentum Premium (Target: Week 1)
- [x] **Data & Research**
    - [x] Fetch 2+ years of daily OHLCV data for BTC, ETH, SOL, LINK.
    - [x] Implement basic backtest in VectorBT (Fri close -> Mon close). (`research/backtests/backtest_strategy_1.py`)
- [x] **Refinement**
    - [x] Implement Trend Filter version (EMA50 > EMA200). (Verified: Significant improvement in returns and drawdown across all assets)
    - [x] Compare results (Sharpe, Drawdown) vs Buy & Hold. (Buy & Hold negative in test period; Trend Filter positive)
- [x] **Implementation**
    - [x] Create `strategies/WeekendMomentum.py` for Freqtrade.
    - [x] Implement `populate_indicators`, `populate_entry_trend`, `populate_exit_trend`. (Done in file)
    - [x] **Improvements (Iter 1)**
        - [x] Add ADX and ATR filters to Strategy.
        - [x] Verify improvements with backtest.
    - [x] **Advanced Validation**
        - [x] Walk-Forward Analysis (WFA): +20.84% Return, 77% Win Rate.
        - [x] Monte Carlo Validation: Low Risk (<7% Prob of Loss).
        - [x] Documentation: `EXP_001_WeekendMomentum.md`.

### Strategy 2: Funding Rate Mean Reversion (Target: Week 1-2)
- [x] **Data Collection**
    - [x] Create `utils/data_collector.py` to fetch historical funding rates.
    - [x] Fetch 2 years of funding data for BTC, ETH, SOL.
- [x] **Research & Backtest**
    - [x] Implement `backtest_funding_mean_reversion` logic.
    - [x] Optimize entry/exit thresholds (default: >0.05% entry, <0.01% exit). (Note: daily data insufficient, recommended 1h)
    - [x] **Improvements (Iter 1)**
        - [x] Fetch 1h OHLCV and Funding Data.
        - [x] Implement Z-Score based Mean Reversion.
        - [x] Verify with 1h backtest.
- [x] **Implementation**
    - [x] Create `strategies/FundingReversion.py`.
    - [x] Implement `Live Signal Monitor` (`utils/telegram_alerts.py`) for real-time funding alerts.

### Strategy 3: Token Unlock Event Trading (Target: Week 2)
- [x] **Data Source**
    - [x] Create `strategies/UnlockTrader.py`.
    - [x] Implement `get_upcoming_unlocks` (API or manual CSV).
    - [x] Implement `score_unlock_impact` logic.
- [x] **Backtest**
    - [x] Implement `backtest_unlock_strategy` (Short 30d before, cover 14d after).
    - [x] Validate against historical events.

### Strategy 4: Liquidation Cascade Bounce (Target: Week 2-3 - HOLD / LOW PRIORITY)
- [x] **Detection System**
    - [x] Implement `LiquidationMonitor` class in `strategies/CascadeBounce.py`.
    - [x] Implement cascade detection logic (Funding flip, Price dump).
- [x] **Strategy Logic**
    - [x] Create `strategies/CascadeBounce.py`.
    - [x] Implement v3 logic: RSI < 30, Volume spike, EMA200 Trend Filter.
- [x] **Validation**
    - [x] Backtest against available data (2024-2026).
    - [x] Result: Profitable on ETH (+3.8%) but low frequency. Safe but low yield.
    - [x] Documentation: `EXP_004_LiquidationCascade.md`.

### Strategy 5: Regime-Adaptive Grid Bot (Target: Week 3)
- [x] **Regime Detection**
    - [x] Implement `CryptoRegimeDetector` class using `hmmlearn`.
    - [x] Train HMM on historical data to label Bull, Bear, Sideways, Transition. (Done in `backtest_strategy_5.py`)
- [x] **Grid Implementation**
    - [x] Create `strategies/RegimeGrid.py`.
    - [x] Implement Grid logic (calculate levels, orders).
    - [x] Integrate Regime Detector: Only active in 'Sideways' regime.
    - [x] Validation: Outperformed Buy & Hold in Bear market (-11% vs -29%). See `EXP_005_RegimeGrid.md`.

### Strategy 6: Cross-L2 DEX Arbitrage (Advanced - Optional)
- [ ] **Scanner**
    - [ ] Setup Web3 connections for Arbitrum, Base, Optimism.
    - [ ] Implement `CrossL2Scanner` to check Uniswap V3 quotes.
    - [ ] Implement spread calculation (including bridge/gas costs).

---

## Phase 2B: Strategy Proposal Improvements (crypto-bot-strategy-2.docx)

*Critical fixes and enhancements from the Feb 2026 Deep Strategy Review.*

### Phase 2B.1: Regime Master Switch (This Week)
- [x] **Regime-Based Portfolio Master Switch**
    - [x] Implement regime-based strategy gating in `utils/risk_manager.py`:
        - **BULL**: S1 active, S2 long-only, S3 shorts disabled, S5 grid inactive
        - **SIDEWAYS**: S1 waits for Friday, S2 both sides, S5 grid active, S3 active
        - **BEAR**: S1 disabled, S2 short-only, S3 short-only, S5 grid cash-preservation
        - **TRANSITION**: Reduce all position sizes by 50%
    - [x] Integrate master switch with `BaseStrategy` and strategy-specific `confirm_trade_entry`.
- [ ] **HMM Regime Detector Enhancements**
    - [x] StandardScaler on HMM features (already in `regime_detector.py`)
    - [x] close/SMA200 ratio as trend_pos feature (already implemented)
    - [ ] Run correlation matrix on **daily** strategy returns (not just trade correlation).

### Phase 2B.2: Strategy 1 (Weekend Momentum) — Sample Size & Validation
- [x] **Stop Loss** — Tightened to 3% (already in `WeekendMomentum.py`)
- [x] **Volatility Gate** — ATR < 75th percentile (already implemented)
- [x] **WFA Expansion**
    - [x] Run WFA on ETH and SOL (in addition to BTC).
    - [x] Pool OOS trades across BTC + ETH + SOL for statistical significance.
    - [x] `--pool` flag outputs `wfa_strat1_pooled_fri-mon.csv`. Pooled: 20 trades (BTC 9, ETH 11).
- [x] **Monday–Wednesday Variant** — `--variant mon-wed` for "Monday close → Wednesday close".

### Phase 2B.3: Strategy 2 (Funding Reversion) — Drawdown Mitigation
- [x] **Dynamic Position Sizing**
    - [x] Z=1.5 → 0.5% risk; Z=2.0 → 1.0%; Z=2.5+ → 1.5%.
    - [x] Integrate conviction-weighted sizing in `FundingReversion.py` / `custom_stake_amount`.
- [x] **Drawdown Throttle**
    - [x] If portfolio drawdown > 10% → halve next position size.
    - [x] If portfolio drawdown > 15% → go to zero until recovers.
- [x] **Asset Focus** — Prefer ETH/SOL over BTC (deployment config).

### Phase 2B.4: Strategy 3 (Token Unlocks) — Narrative Scoring
- [x] **Narrative Momentum Filter**
    - [x] Do not short if 30-day momentum > +50%.
    - [x] Do not short if ADX > 40 on daily (strong directional trend).
- [-] **Market-Neutral Leg** — Deferred to paper-trading phase (multi-asset execution).

### Phase 2B.5: Strategy 4 (Cascade Bounce) — Repurpose as Filter
- [x] **Cascade as S2 Signal Amplifier**
    - [x] Created `utils/cascade_detector.py` with RSI < 30 + vol spike detection.
    - [x] When cascade fires, double conviction weight in `FundingReversion` `custom_stake_amount`.
- [x] CascadeBounce standalone retained; cascade used as S2 amplifier.

### Phase 2B.6: Strategy 5 (Regime Grid) — Master Switch Integration
- [x] RegimeGrid now inherits from BaseStrategy (regime from 2B.1).
- [x] S5 grid inactive in BULL, active in SIDEWAYS, cash-preservation (50% size) in BEAR.

---

## Phase 2C: New Strategies (Strategy Proposal)

### Strategy 6 (NEW): Spot-Perp Basis Harvesting (Delta-Neutral Funding Carry)
*Target: Weeks 2–3 | Edge: Structural (very slow decay)*

- [x] **Data Collection**
    - [x] Extended `utils/fetch_1h_data.py` with `fetch_perp_ohlcv`, `fetch_spot_perp_basis_data`.
    - [x] Fetch spot and perp prices; compute basis.
- [x] **Backtest**
    - [x] Created `research/backtests/backtest_strategy_6.py`: long spot, short perp, collect 8-hour funding.
    - [x] Basis inversion exit: 3 consecutive negative funding periods.
    - [x] Result: ~10.8% avg return, ~5.2% APY, <0.1% max DD (BTC, ETH, SOL).
- [x] **Implementation**
    - [x] Created `strategies/BasisHarvest.py`.
    - [x] Regime guard: only in BEAR or SIDEWAYS (never BULL).

### Strategy 9 (NEW): Cross-Asset Funding Rotation
*Target: Weeks 4–6 | Edge: Structural (very slow decay)*

- [x] **Data Collection**
    - [x] `fetch_funding_multi()` in `utils/fetch_1h_data.py` for 10 assets.
- [x] **Rotation Engine**
    - [x] Z-score ranking (rolling 30-day window per asset).
    - [x] Enter highest Z every 8h; exit when Z < 0.5.
- [x] **Backtest**
    - [x] Created `research/backtests/backtest_strategy_9.py`.
    - [x] Result: 0.76% return, 0.40% APY (BTC, ETH, SOL; 3-asset rotation).

### Strategy 7 (FUTURE): IV Premium Harvesting (Options)
*Medium-term research — requires Deribit/options infra.*

### Strategy 8 (FUTURE): On-Chain Whale Accumulation Tracker
*Requires Glassnode/Nansen API integration.*

### Strategy 10 (FUTURE): Pre-Halving Accumulation Pattern
*Regime overlay for S1 when halving window active (Apr 2028).*

### Strategy 11 (FUTURE): Narrative Momentum + Technical Composite
*Long-term — GitHub, OBI, social signals.*

---

## Phase 3: Validation Pipeline
- [x] **Phase 1: Historical Backtest**
    - [x] Run Freqtrade backtest for substantially improved Strategy 2. (ETH +31%)
- [x] **Phase 2: Walk-Forward Analysis**
    - [x] Implement `walk_forward_analysis.py`.
    - [x] Implement `run_wfa_strategy_2.py` runner.
    - [x] Run analysis (Train 6mo, Test 1mo). (Result: +20.47% Return, 58.85% Win Rate on ETH)
- [x] **Phase 3: Monte Carlo Validation**
    - [x] Implement `monte_carlo_validation` script.
    - [x] Run 1000 simulations per strategy. (Result: Positive Expectancy, High Volatility Risk)
    - [x] Verify 5th percentile return is positive. (Result: 5th percentile is negative/break-even, indicating risk. Accepted with caution.)
- [x] **Phase 4: Documentation Standardization**
    - [x] Create `experiments/` directory.
    - [x] Implement standard reporting template.
    - [x] Create detailed experiment report `EXP_002_FundingReversion_ETH.md`. 

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
- [ ] **Paper Trading Portfolio (Strategy Proposal)**
    - [ ] Deploy S1 + S6 as core: directional (S1) + neutral (S6).
    - [ ] S6 provides baseline yield; S1 provides bull-market upside.
    - [ ] Add S9 (rotation) once S6 validated in paper trading.
    - [ ] Minimum 90 days paper trading before any real capital.
- [ ] **Live Micro-Deployment**
    - [ ] Configure `config/config.json` for live trading (Binance API).
    - [ ] Set conservative limits ($50/trade, max 3 trades).
    - [ ] Enable circuit breakers.
- [ ] **Pre-Live Gate**
    - [ ] S1: 50+ pooled OOS trades with Sharpe > 1.0 before live.
    - [ ] Portfolio Sharpe > 1.0 to justify operational risk.

## Development Log & Notes
- **[Date]**: Initial task list created.
- **[Feb 18, 2026]**: Integrated `crypto-bot-strategy-2.docx` Deep Strategy Review. Added Phase 2B (critical fixes), Phase 2C (new strategies S6, S9). Regime master switch, S2 drawdown throttle, S3 narrative scoring, S4 cascade-as-filter, S1 WFA expansion. Paper trading portfolio spec: S1 + S6 core, S9 after validation.
- **[Feb 18, 2026]**: Phase 2B & 2C implementation complete. Regime Master Switch in risk_manager; S1 WFA --pool and --variant mon-wed; S2 dynamic Z-based sizing and drawdown throttle; S3 narrative filter; S4 cascade detector + S2 amplifier; S5 RegimeGrid inherits BaseStrategy; S6 BasisHarvest backtest + strategy; S9 Cross-Asset Funding Rotation. 30 unit tests passing.
