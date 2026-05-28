import json
import time
from datetime import date, datetime
import httpx
from typing import Optional

from ..config import settings
from ..models.options import OptionsChain, OptionContract
from .base import AbstractProvider, ProviderError, RateLimitError

class EulerpoolProvider(AbstractProvider):
    def __init__(self):
        self.api_key = settings.eulerpool_api_key
        # For Eulerpool, SPX/SPY ISIN might be needed. We'll map ticker to ISIN if known.
        # Known limitation: Eulerpool mostly uses ISIN. 
        # Expanded dictionary mapping Tickers to ISINs for Eulerpool
        self.ticker_to_isin = {
            # --- Global Indices & ETFs ---
            "SPX": "US78378X1072",   # S&P 500 Index
            "SPY": "US78462F1030",   # SPDR S&P 500 ETF
            "NDX": "US6311011026",   # Nasdaq 100 Index
            "QQQ": "US46090E1038",   # Invesco QQQ ETF
            "DJI": "US2605661048",   # Dow Jones Industrial Average
            "RUT": "US78248T1025",   # Russell 2000 Index
            
            # --- Mega-Cap / Blue Chips (US) ---
            "AAPL": "US0378331005",  # Apple Inc.
            "MSFT": "US5949181045",  # Microsoft
            "NVDA": "US67066G1040",  # NVIDIA
            "TSLA": "US88160R1014",  # Tesla
            "AMZN": "US0231351067",  # Amazon
            "GOOGL": "US02079K3059", # Alphabet Class A
            "META": "US30303M1027",  # Meta Platforms
            "BRK.B": "US0846707026", # Berkshire Hathaway Class B
            "JPM": "US46625H1005",   # JPMorgan Chase
            "JNJ": "US4781601046",   # Johnson & Johnson
            "V": "US92826C8394",     # Visa
            "WMT": "US9311421039",   # Walmart
            "PG": "US7427181091",    # Procter & Gamble
            "UNH": "US91324P1021",   # UnitedHealth Group
        }

    @property
    def name(self) -> str:
        return "eulerpool"

    @property
    def provides_greeks(self) -> bool:
        return True

    def _get_cache_path(self, ticker: str) -> str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return settings.cache_dir / f"eulerpool_{ticker}_{date_str}.json"

    def _load_from_cache(self, ticker: str) -> Optional[dict]:
        cache_file = self._get_cache_path(ticker)
        if cache_file.exists():
            # Check TTL
            mtime = cache_file.stat().st_mtime
            if time.time() - mtime < settings.cache_ttl_seconds:
                try:
                    with open(cache_file, "r") as f:
                        return json.load(f)
                except Exception:
                    pass
        return None

    def _save_to_cache(self, ticker: str, data: dict):
        cache_file = self._get_cache_path(ticker)
        with open(cache_file, "w") as f:
            json.dump(data, f)

    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        return True # Can add a lightweight endpoint check here

    async def fetch_options_chain(
        self,
        ticker: str,
        expiration_range: Optional[tuple[date, date]] = None,
        strike_range: Optional[tuple[float, float]] = None,
    ) -> OptionsChain:
        if not self.api_key:
            raise ProviderError("Eulerpool API key not configured")

        cached_data = self._load_from_cache(ticker)
        if cached_data:
            data = cached_data
        else:
            isin = self.ticker_to_isin.get(ticker.upper(), ticker)
            url = f"https://api.eulerpool.com/api/1/equity-extended/options-chain/{isin}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params={"token": self.api_key})
                
                if response.status_code == 429:
                    raise RateLimitError("Eulerpool rate limit exceeded")
                if response.status_code == 404:
                    raise ProviderError(f"Security not found on Eulerpool: {isin}")
                if response.status_code != 200:
                    raise ProviderError(f"Eulerpool API error: {response.text}")
                
                data = response.json()
                self._save_to_cache(ticker, data)

        # Assuming spot_price can be fetched from a generic endpoint or is provided
        # We will use 0.0 for now, and it will be updated by the engine or router
        spot_price = 0.0
        
        contracts = []
        for idx, item in data.items():
            # Filter if needed
            exp_date_str = item.get("expiration_date")
            if not exp_date_str:
                continue
            exp_date = datetime.fromisoformat(exp_date_str.replace("Z", "+00:00")).date()
            
            if expiration_range and (exp_date < expiration_range[0] or exp_date > expiration_range[1]):
                continue
                
            strike = float(item.get("strike", 0))
            if strike_range and (strike < strike_range[0] or strike > strike_range[1]):
                continue

            contract = OptionContract(
                strike=strike,
                expiration=exp_date,
                contract_type="call" if item.get("option_type", "C").upper() == "C" else "put",
                open_interest=int(float(item.get("open_interest", 0))),
                implied_volatility=float(item.get("implied_vol", 0)),
                delta=float(item.get("delta", 0)),
                gamma=float(item.get("gamma", 0)),
                theta=float(item.get("theta", 0)),
                vega=float(item.get("vega", 0)),
            )
            contracts.append(contract)

        return OptionsChain(
            underlying_ticker=ticker,
            spot_price=spot_price,  # Router will inject spot price if missing
            timestamp=datetime.now(),
            contracts=contracts,
            data_source=self.name
        )
