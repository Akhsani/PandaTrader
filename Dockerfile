# PandaTrader Dockerfile
# Based on official Freqtrade image (includes TA-Lib, Python 3.11+)
FROM freqtradeorg/freqtrade:stable

# Install jq for config injection (small, ~1MB)
USER root
RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*
USER ftuser

COPY utils/ /freqtrade/utils/
COPY strategies/ /freqtrade/user_data/strategies/
COPY deploy/config.json /freqtrade/user_data/config.json
COPY deploy/config-funding.json /freqtrade/user_data/config-funding.json
COPY deploy/entrypoint.sh /freqtrade/entrypoint.sh

ENTRYPOINT ["/freqtrade/entrypoint.sh"]
# Paper trading: S1 (Mon-Wed ETH) + S2 (ETH) + S6 (BTC)
# Set API_SERVER_PASSWORD in Railway env for FreqUI; replace STRONG_PASSWORD_HERE via entrypoint
CMD ["trade", \
     "--config", "/freqtrade/user_data/config.json", \
     "--strategy", "WeekendMomentum,FundingReversion,BasisHarvest", \
     "--strategy-path", "/freqtrade/user_data/strategies", \
     "--dry-run-wallet", "1000"]
