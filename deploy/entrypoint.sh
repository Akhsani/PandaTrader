#!/bin/bash
# Inject Railway environment variables into Freqtrade config
# Supports multi-strategy: STRATEGY env selects config (WeekendMomentum->s1, FundingReversion->s2, BasisHarvest->s6)

STRATEGY="${STRATEGY:-WeekendMomentum}"
case "$STRATEGY" in
  WeekendMomentum) CONFIG_SRC="/freqtrade/user_data/config-s1.json" ;;
  FundingReversion) CONFIG_SRC="/freqtrade/user_data/config-s2.json" ;;
  BasisHarvest) CONFIG_SRC="/freqtrade/user_data/config-s6.json" ;;
  *) CONFIG_SRC="/freqtrade/user_data/config.json" ;;
esac
[ -f "$CONFIG_SRC" ] && cp "$CONFIG_SRC" /freqtrade/user_data/config.json

CONFIGS=("/freqtrade/user_data/config.json" "/freqtrade/user_data/config-funding.json")

for CONFIG in "${CONFIGS[@]}"; do
    [ -f "$CONFIG" ] || continue

    # Use jq to inject secrets (Railway: EXCHANGE_API_KEY or BINANCE_KEY)
    KEY="${EXCHANGE_API_KEY:-$BINANCE_KEY}"
    SECRET="${EXCHANGE_API_SECRET:-$BINANCE_SECRET}"
    if [ -n "$KEY" ]; then
        TMP=$(mktemp)
        jq --arg key "$KEY" --arg secret "$SECRET" \
           '.exchange.key = $key | .exchange.secret = $secret' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"
    fi

    # Railway: TELEGRAM_BOT_TOKEN or TELEGRAM_TOKEN
    TG_TOKEN="${TELEGRAM_BOT_TOKEN:-$TELEGRAM_TOKEN}"
    if [ -n "$TG_TOKEN" ]; then
        TMP=$(mktemp)
        jq --arg token "$TG_TOKEN" --arg chat "$TELEGRAM_CHAT_ID" \
           '.telegram.token = $token | .telegram.chat_id = $chat' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"
    fi

    # API server password (Railway: API_SERVER_PASSWORD)
    if [ -n "$API_SERVER_PASSWORD" ]; then
        TMP=$(mktemp)
        jq --arg pwd "$API_SERVER_PASSWORD" '.api_server.password = $pwd' "$CONFIG" > "$TMP" && mv "$TMP" "$CONFIG"
    fi
done

# Execute Freqtrade with STRATEGY from env (enables multi-service deployment)
exec freqtrade trade \
  --config /freqtrade/user_data/config.json \
  --strategy "$STRATEGY" \
  --strategy-path /freqtrade/user_data/strategies \
  --dry-run-wallet 1000
