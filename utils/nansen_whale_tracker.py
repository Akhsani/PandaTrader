"""
Strategy 8: On-Chain Whale Accumulation Tracker
Wrapper around Nansen API for Smart Money netflow and accumulation signals.
Uses liquid assets (BTC/WBTC, ETH/WETH, SOL) initially; expandable to mid-caps.
"""
import os
import json
import logging
from typing import Optional
from datetime import datetime

import requests
import pandas as pd

logger = logging.getLogger(__name__)

# Token mapping: symbol -> (chain, token_address)
# Phase 1 (liquid): WBTC, WETH, SOL
# Phase 2 (mid-caps): AVAX, LINK, ARB, OP — expand after validation
TOKEN_MAP = {
    'BTC': ('ethereum', '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599'),   # WBTC
    'ETH': ('ethereum', '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'),   # WETH
    'SOL': ('solana', 'So11111111111111111111111111111111111111112'),    # SOL native
    # Mid-caps (Phase 2 — enable after liquid validation)
    'AVAX': ('avalanche', '0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7'),   # WAVAX
    'LINK': ('ethereum', '0x514910771af9ca656af840dff83e8264ecf986ca'),   # LINK
    'ARB': ('arbitrum', '0x912ce59144191c1204e64559fe8253a0e49e6548'),    # ARB
    'OP': ('optimism', '0x4200000000000000000000000000000000000042'),     # OP
}

# Symbol to trading pair mapping for Freqtrade
SYMBOL_TO_PAIR = {
    'BTC': 'BTC/USDT',
    'ETH': 'ETH/USDT',
    'SOL': 'SOL/USDT',
    'AVAX': 'AVAX/USDT',
    'LINK': 'LINK/USDT',
    'ARB': 'ARB/USDT',
    'OP': 'OP/USDT',
}

# Liquid assets (Phase 1 — default)
S8_LIQUID_UNIVERSE = ['BTC', 'ETH', 'SOL']

# Mid-caps (Phase 2 — use after validation)
S8_MIDCAP_UNIVERSE = ['AVAX', 'LINK', 'ARB', 'OP']

NANSEN_BASE_URL = "https://api.nansen.ai"
DEFAULT_CACHE_DIR = "data/whale_signals"


class NansenWhaleTracker:
    """
    Fetches Smart Money netflow data from Nansen API and computes accumulation scores.
    """

    def __init__(self, api_key: Optional[str] = None, cache_dir: Optional[str] = None):
        self.api_key = api_key or os.environ.get('NANSEN_API_KEY', '')
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        os.makedirs(self.cache_dir, exist_ok=True)

    def _request(self, endpoint: str, payload: dict) -> Optional[dict]:
        """Make POST request to Nansen API."""
        if not self.api_key:
            logger.warning("Nansen API key not set. Set NANSEN_API_KEY env var.")
            return None

        url = f"{NANSEN_BASE_URL}{endpoint}"
        headers = {
            'Content-Type': 'application/json',
            'apikey': self.api_key,  # lowercase per Nansen docs
        }
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') and e.response else None
            body = ''
            if hasattr(e, 'response') and e.response is not None:
                try:
                    body = e.response.text[:500] if e.response.text else ''
                except Exception:
                    pass
            if status == 422:
                logger.debug(f"Nansen API 422 (validation): {e} {body}")
            elif status == 403:
                msg = "TGM flows require credits/subscription. "
                if "credits" in body.lower():
                    msg = "Insufficient Nansen credits for TGM flows. "
                logger.error(
                    f"Nansen API 403: {msg}"
                    f"Add credits at app.nansen.ai or use --allow-synthetic for backtest. {body[:200]}"
                )
            else:
                logger.error(f"Nansen API request failed: {e} {body}")
            return None

    def get_smart_money_netflow(
        self,
        chains: Optional[list] = None,
        token_addresses: Optional[list] = None,
        order_by: str = 'net_flow_24h_usd',
        direction: str = 'DESC',
        per_page: int = 25,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch Smart Money netflow data.
        Returns DataFrame with token_address, token_symbol, net_flow_1h_usd, net_flow_24h_usd,
        net_flow_7d_usd, net_flow_30d_usd, chain, market_cap_usd.
        """
        chains = chains or ['ethereum', 'solana']
        payload = {
            'chains': chains,
            'filters': {
                'include_native_tokens': True,
            },
            'pagination': {'page': 1, 'per_page': per_page},
            'order_by': [{'field': order_by, 'direction': direction}],
        }
        if token_addresses:
            payload['filters']['token_address'] = token_addresses

        data = self._request('/api/v1/smart-money/netflow', payload)
        if not data or 'data' not in data:
            return None

        df = pd.DataFrame(data['data'])
        return df

    def get_netflow_for_tokens(
        self,
        symbols: list[str] = None,
    ) -> pd.DataFrame:
        """
        Get netflow for specific tokens (BTC, ETH, SOL by default).
        Returns DataFrame with symbol, chain, net_flow_24h_usd, net_flow_7d_usd, etc.
        """
        symbols = symbols or list(TOKEN_MAP.keys())
        token_addresses = [TOKEN_MAP[s][1] for s in symbols if s in TOKEN_MAP]
        chains = list(set(TOKEN_MAP[s][0] for s in symbols if s in TOKEN_MAP))

        df = self.get_smart_money_netflow(
            chains=chains,
            token_addresses=token_addresses if token_addresses else None,
            per_page=50,
        )
        if df is None or df.empty:
            return pd.DataFrame()

        # Map token_address back to symbol (EVM addresses: case-insensitive)
        addr_to_sym = {}
        for k, (chain, addr) in TOKEN_MAP.items():
            addr_to_sym[addr.lower() if addr.startswith('0x') else addr] = k
        token_sym_map = {'WBTC': 'BTC', 'WETH': 'ETH', 'ETH': 'ETH', 'BTC': 'BTC', 'SOL': 'SOL'}

        def _to_symbol(row):
            addr = str(row.get('token_address', ''))
            addr_key = addr.lower() if addr.startswith('0x') else addr
            if addr_key in addr_to_sym:
                return addr_to_sym[addr_key]
            ts = str(row.get('token_symbol', '')).upper()
            return token_sym_map.get(ts, ts or 'UNK')

        df['symbol'] = df.apply(_to_symbol, axis=1)
        return df

    def compute_accumulation_score(
        self,
        net_flow_24h_usd: float,
        net_flow_7d_usd: float,
        market_cap_usd: Optional[float] = None,
        min_flow_24h: float = 100_000,
        fdv_weight: float = 0.0,
    ) -> float:
        """
        Compute accumulation score from netflow data.
        Higher score = stronger Smart Money accumulation.
        Uses 24h and 7d net flow; optionally normalizes by market cap.
        """
        if net_flow_24h_usd is None or pd.isna(net_flow_24h_usd):
            net_flow_24h_usd = 0
        if net_flow_7d_usd is None or pd.isna(net_flow_7d_usd):
            net_flow_7d_usd = 0

        # Base score: positive flow = positive score
        score_24h = max(0, net_flow_24h_usd) / max(min_flow_24h, 1)
        score_7d = max(0, net_flow_7d_usd) / max(min_flow_24h * 7, 1)
        score = 0.6 * min(score_24h, 10) + 0.4 * min(score_7d / 7, 10)

        if market_cap_usd and market_cap_usd > 0 and fdv_weight > 0:
            flow_pct = (net_flow_24h_usd + net_flow_7d_usd) / market_cap_usd
            score += fdv_weight * min(flow_pct * 1000, 5)

        return round(score, 4)

    def get_accumulation_scores(
        self,
        symbols: list[str] = None,
        min_flow_24h: float = 100_000,
        threshold: float = 0.5,
    ) -> dict[str, dict]:
        """
        Get accumulation scores for target tokens.
        Returns dict: symbol -> {score, net_flow_24h_usd, net_flow_7d_usd, signal}
        signal=True when score >= threshold.
        """
        df = self.get_netflow_for_tokens(symbols)
        if df.empty:
            return {}

        result = {}
        for _, row in df.iterrows():
            sym = row.get('symbol', row.get('token_symbol', 'UNK'))
            if pd.isna(sym):
                continue
            sym = str(sym).upper()
            if sym in ['WBTC']:
                sym = 'BTC'
            elif sym in ['WETH']:
                sym = 'ETH'

            nf24 = row.get('net_flow_24h_usd', 0) or 0
            nf7d = row.get('net_flow_7d_usd', 0) or 0
            mcap = row.get('market_cap_usd')

            score = self.compute_accumulation_score(
                nf24, nf7d, mcap, min_flow_24h=min_flow_24h
            )
            result[sym] = {
                'score': score,
                'net_flow_24h_usd': nf24,
                'net_flow_7d_usd': nf7d,
                'market_cap_usd': mcap,
                'signal': score >= threshold,
            }
        return result

    def cache_scores(self, scores: dict, filename: Optional[str] = None) -> str:
        """Cache accumulation scores to disk."""
        filename = filename or f"whale_scores_{datetime.utcnow().strftime('%Y%m%d_%H%M')}.json"
        path = os.path.join(self.cache_dir, filename)
        with open(path, 'w') as f:
            json.dump(scores, f, indent=2)
        return path

    def load_cached_scores(self, path: str) -> Optional[dict]:
        """Load cached scores from file."""
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    # Native tokens not supported by TGM flows (per Nansen docs)
    _UNSUPPORTED_FLOWS_TOKENS = {
        'So11111111111111111111111111111111111111112',  # SOL native
        '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',   # ETH native (avalanche, etc.)
    }

    def get_token_flows(
        self,
        chain: str,
        token_address: str,
        date_from: str,
        date_to: str,
        label: str = 'smart_money',
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical token flows for backtest.
        date_from, date_to: ISO 8601 format (e.g. '2024-01-01', '2024-12-31').
        Returns None for unsupported native tokens (avoids 422).
        """
        if token_address in self._UNSUPPORTED_FLOWS_TOKENS:
            return None
        payload = {
            'chain': chain,
            'token_address': token_address,
            'date': {'from': date_from, 'to': date_to},
            'label': label,
            'pagination': {'page': 1, 'per_page': 1000},
        }
        data = self._request('/api/v1/tgm/flows', payload)
        if not data or 'data' not in data:
            return None
        df = pd.DataFrame(data['data'])
        if not df.empty and 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
        return df
