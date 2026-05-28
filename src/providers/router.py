import logging
from datetime import date
from typing import Optional

from ..models.options import OptionsChain
from .base import AbstractProvider, ProviderError, RateLimitError
from .eulerpool import EulerpoolProvider
from .polygon import PolygonProvider
from .yahoo import YahooProvider

logger = logging.getLogger(__name__)

class AllProvidersFailedError(Exception):
    pass

class ProviderRouter:
    def __init__(self, provider_order: list[str]):
        # Initialize providers
        available_providers = {
            "eulerpool": EulerpoolProvider(),
            "polygon": PolygonProvider(),
            "yahoo": YahooProvider(),
        }
        
        # Order them based on config
        self._providers = []
        for name in provider_order:
            if name in available_providers:
                self._providers.append(available_providers[name])
                
        self._health: dict[str, bool] = {}

    async def fetch_chain(
        self,
        ticker: str,
        expiration_range: Optional[tuple[date, date]] = None,
        strike_range: Optional[tuple[float, float]] = None,
    ) -> OptionsChain:
        """
        Attempts to fetch options chain cascading through providers based on priority.
        """
        errors = []
        
        for provider in self._providers:
            # Check if we should skip due to previous health check failure
            if not self._health.get(provider.name, True):
                continue
                
            try:
                is_healthy = await provider.health_check()
                if not is_healthy:
                    self._health[provider.name] = False
                    continue
                    
                logger.info(f"Attempting to fetch data from {provider.name} for {ticker}...")
                chain = await provider.fetch_options_chain(
                    ticker=ticker,
                    expiration_range=expiration_range,
                    strike_range=strike_range
                )
                logger.info(f"Successfully fetched data from {provider.name}")
                return chain
                
            except RateLimitError as e:
                logger.warning(f"Rate limit exceeded for {provider.name}: {e}")
                self._health[provider.name] = False
                errors.append(f"{provider.name} (RateLimit): {e}")
            except ProviderError as e:
                logger.warning(f"Provider error for {provider.name}: {e}")
                errors.append(f"{provider.name} (Error): {e}")
            except Exception as e:
                logger.error(f"Unexpected error from {provider.name}: {e}")
                errors.append(f"{provider.name} (Unexpected): {e}")
                
        raise AllProvidersFailedError(f"All providers failed to fetch data. Errors: {errors}")

def get_router(provider_order: list[str]) -> ProviderRouter:
    return ProviderRouter(provider_order)
