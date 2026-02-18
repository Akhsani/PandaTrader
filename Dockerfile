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
COPY deploy/config-s1.json /freqtrade/user_data/config-s1.json
COPY deploy/config-s2.json /freqtrade/user_data/config-s2.json
COPY deploy/config-s6.json /freqtrade/user_data/config-s6.json
COPY deploy/config-funding.json /freqtrade/user_data/config-funding.json
COPY deploy/entrypoint.sh /freqtrade/entrypoint.sh

ENTRYPOINT ["/freqtrade/entrypoint.sh"]
# STRATEGY env selects config: WeekendMomentum (S1) | FundingReversion (S2) | BasisHarvest (S6)
# Default: WeekendMomentum. Set STRATEGY in Railway vars per service.
CMD ["trade"]
