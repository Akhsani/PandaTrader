# PandaTrader — Task List
> Updated: February 18, 2026 · Phase: Pre-Paper Trading · Hosting: Railway.app

**Current status:** Multi-strategy deployment. 3 services: PandaTrader (S1), PandaTrader-S2, PandaTrader-S6. Each runs one strategy. **Copy env vars** (EXCHANGE_API_KEY, TELEGRAM_BOT_TOKEN, etc.) to S2 and S6 in Railway dashboard.

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

- [x] **Create Railway project**
  - Project "cozy-harmony" with 3 services: PandaTrader (S1), PandaTrader-S2, PandaTrader-S6
  - Each service: same repo, `STRATEGY` env selects config (WeekendMomentum | FundingReversion | BasisHarvest)

- [ ] **Add persistent Volume**
  - Mount path: `/freqtrade/user_data`
  - Hobby plan: up to 5 GB (more than enough)
  - This preserves `tradesv3.sqlite` across redeploys — **do not skip**

- [x] **Set environment variables in Railway dashboard**
  - `EXCHANGE_API_KEY`, `EXCHANGE_API_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `API_SERVER_PASSWORD`, `FREQTRADE_ENV` — all set
  - **⚠️ Telegram fix:** If you see "bots can't send messages to bots" — your `TELEGRAM_CHAT_ID` is wrong. Use your **personal** chat ID (from `getUpdates` after messaging your bot), NOT the bot's ID. The bot token format is `bot_id:secret` — do not use `bot_id` as chat_id.

  **How to get Telegram Chat ID**
  1. Create a bot via [@BotFather](https://t.me/BotFather): send `/newbot`, follow prompts, copy the token → `TELEGRAM_BOT_TOKEN`
  2. Start a chat with your bot (click its link, send any message like `/start`)
  3. Get your chat ID:
     - **Option A:** Visit `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates` in a browser (replace `<YOUR_BOT_TOKEN>`). After you messaged the bot, the JSON response will show `"chat":{"id":123456789}` — that number is your `TELEGRAM_CHAT_ID`
     - **Option B:** Use [@userinfobot](https://t.me/userinfobot) — forward a message from your bot to it, or message it directly; it replies with your ID
  4. For a **group chat:** Add the bot to the group, send a message, then use `getUpdates` — the group ID will be negative (e.g. `-1001234567890`)

  **API_SERVER_PASSWORD**
  - **What it is:** The password for FreqUI (FreqTrade’s web dashboard). Used to log in at `https://your-app.up.railway.app`
  - **How to get it:** You choose it. Create a strong password (e.g. 16+ chars, mixed case, numbers, symbols)
  - **Where to set:** Railway → Service → Variables → add `API_SERVER_PASSWORD` = your chosen password
  - **Username:** Fixed as `pandatrader` in config (or change in `deploy/config.json`)
  - **Note:** If unset, the config uses `STRONG_PASSWORD_HERE` — change this before going live

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

- [x] **Expose port 8080 in Railway service settings**
  - Domain: `https://pandatrader-production.up.railway.app`

- [x] **Verify FreqUI loads at Railway domain after first deploy**
  - Bot RUNNING; API server on 8080; WeekendMomentum strategy active
  - Login: username `pandatrader`, password = your `API_SERVER_PASSWORD`

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

- [x] **Multi-strategy Railway setup**
  - S1 (PandaTrader): `STRATEGY=WeekendMomentum` (default), spot, BTC+ETH, $600 wallet
  - S2 (PandaTrader-S2): `STRATEGY=FundingReversion`, futures ETH, $600 wallet
  - S6 (PandaTrader-S6): `STRATEGY=BasisHarvest`, futures BTC, $300 wallet
  - **Action required:** Copy env vars from PandaTrader to S2 and S6: EXCHANGE_API_KEY, EXCHANGE_API_SECRET, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, API_SERVER_PASSWORD
  - Generate domains for S2/S6 in Railway → Service → Settings → Networking

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

## 🤖 3Commas Bot Simulators (Local)

| Strategy | Bot Type | Status | Gate |
|----------|----------|--------|------|
| S-A RSI DCA | DCA | Validated | PASS |
| S-B Grid ETH | Grid | Validated | PASS |
| S-D EMA Signal | Signal | Gate Failed | FAIL |

**Docs:** [BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md](research/reports/BOT_TEST_RESULTS_AND_RECOMMENDATIONS.md) | [BOT_WORKFLOW.md](docs/BOT_WORKFLOW.md)

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

| Service | Strategy | FreqUI |
|---------|----------|--------|
| PandaTrader | S1 WeekendMomentum | `https://pandatrader-production.up.railway.app` |
| PandaTrader-S2 | S2 FundingReversion | `https://pandatrader-s2-production.up.railway.app` |
| PandaTrader-S6 | S6 BasisHarvest | `https://pandatrader-s6-production.up.railway.app` |

| Layer | Tool |
|-------|------|
| Push alerts | **Telegram bot** — all 3 services share same bot/chat |
| CPU / RAM / logs | **Railway dashboard** |

> Grafana / Freqdash not needed until live capital + 3 months of data worth visualizing.