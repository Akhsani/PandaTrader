# PandaTrader Dockerfile
# Based on official Freqtrade image (includes TA-Lib, Python 3.11+)
FROM freqtradeorg/freqtrade:stable

# Install jq for config injection + Python deps for regime detection
USER root
RUN apt-get update && apt-get install -y jq && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir hmmlearn scikit-learn
USER ftuser

COPY utils/ /freqtrade/utils/
COPY strategies/ /freqtrade/user_data/strategies/
COPY deploy/config.json /freqtrade/user_data/config.json
COPY deploy/config-funding.json /freqtrade/user_data/config-funding.json
COPY deploy/entrypoint.sh /freqtrade/entrypoint.sh

ENTRYPOINT ["/freqtrade/entrypoint.sh"]
# Paper trading: FreqTrade supports single strategy per bot. Using WeekendMomentum (S1).
# For S2+S6, add separate Railway services. Set API_SERVER_PASSWORD in Railway env.
CMD ["trade", \
     "--config", "/freqtrade/user_data/config.json", \
     "--strategy", "WeekendMomentum", \
     "--strategy-path", "/freqtrade/user_data/strategies", \
     "--dry-run-wallet", "1000"]
