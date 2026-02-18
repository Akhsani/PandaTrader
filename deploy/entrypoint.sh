#!/bin/bash
# Inject Railway environment variables into Freqtrade config
# This avoids putting secrets in config.json (which is in git)

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

# Execute the original Freqtrade command
exec freqtrade "$@"
