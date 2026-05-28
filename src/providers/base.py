from abc import ABC, abstractmethod
from datetime import date
from typing import Optional

from ..models.options import OptionsChain

class ProviderError(Exception):
    """Base exception for provider errors"""
    pass

class RateLimitError(ProviderError):
    """Raised when provider rate limit is hit"""
    pass

class AbstractProvider(ABC):
    @abstractmethod
    async def fetch_options_chain(
        self,
        ticker: str,
        expiration_range: Optional[tuple[date, date]] = None,
        strike_range: Optional[tuple[float, float]] = None,
    ) -> OptionsChain:
        """Fetch options chain from the provider."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available and healthy."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    @abstractmethod
    def provides_greeks(self) -> bool:
        """Does this provider supply pre-calculated Greeks?"""
        pass
