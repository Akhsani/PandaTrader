# PandaTrader — Task List
> Updated: February 18, 2026 · Phase: Pre-Paper Trading · Hosting: Railway.app

---

## Status Legend
- `[ ]` Todo
- `[~]` In Progress
- `[x]` Done
- `[-]` Skipped / Deferred

---

## 🔴 PHASE 3A — Paper Trading Pre-Flight (Days 1–5)
*Blockers. Nothing deploys until these are done.*

### Railway Infrastructure Setup

- [ ] **Create Railway project**
  - New project → "PandaTrader"
  - Add service → deploy from GitHub repo (or Docker image)

- [ ] **Add persistent Volume**
  - Mount path: `/freqtrade/user_data`
  - Hobby plan: up to 5 GB (more than enough)
  - This preserves `tradesv3.sqlite` across redeploys — **do not skip**

- [ ] **Set environment variables in Railway dashboard**
  - `EXCHANGE_API_KEY`
  - `EXCHANGE_API_SECRET`
  - `TELEGRAM_BOT_TOKEN`
  - `TELEGRAM_CHAT_ID`
  - `FREQTRADE_ENV=dry_run`
  - Never hardcode secrets in config files

- [x] **Create `Dockerfile` (if not already)**
  - Exists; copies strategies, config; CMD runs S1+S2+S6

- [x] **Configure FreqTrade REST API for Railway**
  - Listen on `0.0.0.0` (not `127.0.0.1`) so Railway's proxy can reach it
  - Set CORS to your Railway domain
  ```json
  "api_server": {
    "enabled": true,
    "listen_ip_address": "0.0.0.0",
    "listen_port": 8080,
    "username": "pandatrader",
    "password": "STRONG_PASSWORD_HERE",
    "CORS_origins": ["https://pandatrader.up.railway.app"]
  }
  ```
  - Railway auto-provisions HTTPS — FreqUI accessible at `https://pandatrader.up.railway.app`

- [x] **Set db_url to mounted volume path**
  - Added to `deploy/config.json`

- [ ] **Expose port 8080 in Railway service settings**
  - Railway → Service → Settings → Networking → add port 8080
  - Generate Railway domain

- [ ] **Verify FreqUI loads at Railway domain after first deploy**
  - Login with credentials set above
  - Confirm dry-run trades are visible

### Strategy Pre-Flight

- [x] **S1: Add Mon–Wed mode to `WeekendMomentum.py`**
  - Added `mode` CategoricalParameter (`fri-mon` | `mon-wed`)
  - `mon-wed`: enter Mon (day 0), exit Wed (day 2); ETH/USDT only

- [x] **S6: Hardcode `ENTRY_THRESHOLD = 0.00005` everywhere**
  - `utils/funding_utils.py` — single source of truth
  - `strategies/BasisHarvest.py` and `research/backtests/backtest_strategy_6.py` import it

- [x] **S2: Run backtest with Cascade Amplifier ON**
  - 2× stake: MaxDD 54% (ETH) — exceeds 25%
  - Reduced to 1.5× in `FundingReversion.py`; fixed-param backtest DD still ~52%
  - Note: WFA (+44.64% ETH) uses rolling params; cascade amplifier kept at 1.5× for paper

- [x] **FreqTrade dry-run config** (`deploy/config.json`)
  - Strategies: WeekendMomentum, FundingReversion, BasisHarvest (S1+S2+S6)
  - `"dry_run": true`, `"dry_run_wallet": 1000`
  - api_server enabled, db_url set, pair_whitelist BTC+ETH

- [ ] **Wire Telegram daily report to live FreqTrade state**
  - Pull P&L from FreqTrade REST API (not mocked data): `GET /api/v1/profit`
  - Report: portfolio equity, daily PnL, open trades, current regime, S6 last funding received
  - Telegram token/chat ID loaded from Railway env vars (not hardcoded)

---

## 🟡 PHASE 3B — Parallel Improvements (Week 2–3)
*Run alongside paper trading. Don't block go-live.*

- [ ] **Replace Nansen S8 with free signals**
  - ETH: integrate Glassnode free API → `Exchange Net Position Change` (daily)
  - SOL: rename to `SOL Momentum Strategy` — remove Nansen dependency entirely
  - BTC: add CryptoQuant free `Exchange Whale Ratio` as secondary filter
  - Cancel Nansen subscription ($49/month saved)

- [ ] **Upgrade HMM Regime Detector**
  - Add `StandardScaler` to all 4 features before HMM fitting
  - Add 5th feature: `close / SMA200` ratio (macro trend position)
  - Retrain, visually verify labels against known BTC market periods (2024 bull, 2025 correction)

- [ ] **S9: Expand to 10 assets**
  - Add AVAX, APT, SUI, OP, ARB, BNB, TIA to funding rate collector
  - Re-run Z-score rotation backtest over 2-year period
  - Only deploy S9 if yield > S6 single-asset after 10-asset test

- [ ] **S3: Clean up `UnlockTrader.py`**
  - Remove graduated sizing code (confirmed to underperform fixed sizing)
  - Add comment: `"Fixed sizing only — graduated sizing tested in EXP_003, no improvement"`
  - Keep narrative filter (ADX < 40, mom < 50%) for risk control

- [ ] **Railway: connect GitHub repo for auto-deploy**
  - Auto-redeploy on push to `main`
  - Use Railway's one-click rollback if a bad deploy breaks paper trading

---

## 🟢 PHASE 3C — Paper Trading Validation Gates (Ongoing)

### Weekly Checks
- [ ] Check FreqUI at Railway domain — open trades, P&L curve, fee totals
- [ ] Compare paper win rate vs WFA win rate (flag if delta > 15%)
- [ ] Log each S6 funding payment (8H interval) — confirm positive flow
- [ ] Check Railway dashboard: CPU/RAM not spiking (sign of runaway loop or API hammering)
- [ ] Verify S2 dynamic sizing firing correctly at Z thresholds

### Monthly Checks
- [ ] Re-optimize S2 ETH params on latest 180 days (`reoptimize_strategy_2.py`)
- [ ] Run correlation matrix on 30-day paper daily returns (confirm near-zero across S1/S2/S6)
- [ ] HMM regime check — does current label match market reality?
- [ ] Review Railway billing — confirm usage staying under Hobby $5 credit

### Go/No-Go Gate: Live Micro-Deployment (After 30 Days Paper)
- [ ] Portfolio Sharpe > 0.8 → proceed
- [ ] Max drawdown < 10% → proceed
- [ ] Paper win rates within 15% of WFA win rates → proceed
- [ ] All three pass → deploy $100–200 live capital (flip `"dry_run": false` in Railway env vars)

---

## ✅ COMPLETED (Phase 1 & 2)

### Infrastructure
- [x] Environment setup (Python venv, CCXT, FreqTrade, VectorBT, TA-Lib)
- [x] Project directory structure
- [x] DNS patch for Binance API
- [x] Risk manager (`risk_manager.py`) — kill switch, daily loss limit, position sizing
- [x] Regime detector (HMM, 4 features)
- [x] Regime master switch — `set_regime()`, `is_strategy_allowed()`, `get_position_size_multiplier()`
- [x] `BaseStrategy` with regime sync + gating in `confirm_trade_entry`
- [x] Telegram alerts (`telegram_alerts.py`)
- [x] Backtest utils — fees, slippage, performance metrics
- [x] Walk-forward analysis pipeline
- [x] Monte Carlo validation (1000 simulations)

### Strategies
- [x] **S1 Weekend Momentum** — EMA filter, ATR gate, WFA validated (BTC 9 trades, ETH 11 trades, Mon–Wed ETH 30 trades / 70% win / 39.34%)
- [x] **S2 Funding Reversion** — Z-score entry, ADX filter, dynamic sizing, drawdown throttle, WFA +44.64% ETH
- [x] **S3 Token Unlocks** — Narrative filter (ADX/momentum), fixed sizing, ARB/OP/SUI approved
- [x] **S4 Cascade Bounce** — repurposed as S2 amplifier (cascade detector + 2× stake)
- [x] **S5 Regime Grid** — master switch integrated, SIDEWAYS-only activation
- [x] **S6 Basis Harvest** — spot long + perp short, 8H funding, entry threshold = 0.00005, 16.42% return
- [x] **S8 Whale Accumulation** — Nansen TGM integrated; conclusion: SOL synthetic only (no Nansen needed)
- [x] **S9 Cross-Asset Rotation** — built, tested; underperforms S6 at 3 assets; defer until 10-asset

### Validation
- [x] WFA for S1 (BTC, ETH pooled, Mon–Wed variant)
- [x] WFA for S2 (ETH — 213 trades)
- [x] Monte Carlo for S1 (pooled), S2 (ETH), S8 (pooled)
- [x] Correlation analysis — S1/S2/S6 near-zero correlation confirmed
- [x] 30 unit tests passing

---

## 📊 Current Strategy Status

| Strategy | Asset | Status | Paper Deploy? |
|----------|-------|--------|--------------|
| S1 Mon–Wed | ETH | ✅ Ready (after FreqTrade config) | YES |
| S2 Funding | ETH only | ✅ Ready (monthly re-opt required) | YES |
| S3 Unlocks | ARB, OP, SUI | ⚠️ Manual event-driven | ON SIGNAL |
| S5 Regime Grid | BTC | ✅ Overlay only | YES (auto) |
| S6 Basis | BTC | ✅ Ready (threshold fix first) | YES |
| S8 Whale (SOL) | SOL | 🔄 Rebuild as free momentum | AFTER REBUILD |
| S9 Rotation | — | ❌ Need 10 assets | DEFERRED |

---

## 🖥️ Monitoring Stack (Railway)

| Layer | Tool | Access |
|-------|------|--------|
| Live trades & charts | **FreqUI** | `https://pandatrader.up.railway.app` |
| Push alerts | **Telegram bot** | Trade open/close, daily summary, errors |
| CPU / RAM / logs | **Railway dashboard** | Built-in, no setup needed |

> Grafana / Freqdash not needed until live capital + 3 months of data worth visualizing.