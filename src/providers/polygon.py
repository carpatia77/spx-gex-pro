from datetime import date, datetime
from typing import Optional

from ..config import settings
from ..models.options import OptionsChain, OptionContract
from .base import AbstractProvider, ProviderError, RateLimitError

class PolygonProvider(AbstractProvider):
    def __init__(self):
        self.api_key = settings.polygon_api_key
        try:
            from polygon import RESTClient
            self.client = RESTClient(api_key=self.api_key) if self.api_key else None
        except ImportError:
            self.client = None

    @property
    def name(self) -> str:
        return "polygon"

    @property
    def provides_greeks(self) -> bool:
        return True

    async def health_check(self) -> bool:
        return self.client is not None

    async def fetch_options_chain(
        self,
        ticker: str,
        expiration_range: Optional[tuple[date, date]] = None,
        strike_range: Optional[tuple[float, float]] = None,
    ) -> OptionsChain:
        if not self.client:
            raise ProviderError("Polygon API key not configured or client not installed")

        poly_ticker = "I:SPX" if ticker.upper() == "SPX" else ticker
        
        # We need to handle pagination manually or use the client's generator
        contracts = []
        spot_price = 0.0
        
        try:
            # We use an empty dict for params since polygon client handles kwargs poorly sometimes,
            # but we can filter after fetching or use exact params if known.
            params = {}
            if expiration_range:
                params["expiration_date.gte"] = expiration_range[0].strftime("%Y-%m-%d")
                params["expiration_date.lte"] = expiration_range[1].strftime("%Y-%m-%d")
            if strike_range:
                params["strike_price.gte"] = strike_range[0]
                params["strike_price.lte"] = strike_range[1]
                
            # Fetch options snapshot
            for item in self.client.list_snapshot_options_chain(underlying_asset=poly_ticker, **params):
                if not spot_price and hasattr(item, 'underlying_asset') and item.underlying_asset:
                    spot_price = item.underlying_asset.price
                
                details = item.details
                if not details:
                    continue
                    
                greeks = item.greeks
                
                contracts.append(OptionContract(
                    strike=float(details.strike_price),
                    expiration=datetime.strptime(details.expiration_date, "%Y-%m-%d").date(),
                    contract_type=details.contract_type,
                    open_interest=int(item.open_interest or 0),
                    implied_volatility=float(item.implied_volatility or 0),
                    delta=float(greeks.delta) if greeks and greeks.delta is not None else None,
                    gamma=float(greeks.gamma) if greeks and greeks.gamma is not None else None,
                    theta=float(greeks.theta) if greeks and greeks.theta is not None else None,
                    vega=float(greeks.vega) if greeks and greeks.vega is not None else None,
                ))
        except Exception as e:
            if "429" in str(e):
                raise RateLimitError(f"Polygon rate limit: {e}")
            raise ProviderError(f"Polygon API error: {e}")

        return OptionsChain(
            underlying_ticker=ticker,
            spot_price=spot_price,
            timestamp=datetime.now(),
            contracts=contracts,
            data_source=self.name
        )
