import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.models.options import OptionsChain, OptionContract
from src.providers.router import ProviderRouter, AllProvidersFailedError
from src.providers.base import ProviderError, RateLimitError

@pytest.fixture
def mock_chain():
    return OptionsChain(
        underlying_ticker="AAPL",
        spot_price=150.0,
        timestamp=None,
        contracts=[],
        data_source="mock"
    )

@pytest.mark.asyncio
async def test_router_success_first_provider(mock_chain):
    router = ProviderRouter(["eulerpool", "polygon", "yahoo"])
    
    with patch('src.providers.eulerpool.EulerpoolProvider.health_check', return_value=True), \
         patch('src.providers.eulerpool.EulerpoolProvider.fetch_options_chain', return_value=mock_chain):
        
        result = await router.fetch_chain("AAPL")
        assert result.underlying_ticker == "AAPL"
        assert result.data_source == "mock"

@pytest.mark.asyncio
async def test_router_fallback(mock_chain):
    router = ProviderRouter(["eulerpool", "polygon", "yahoo"])
    
    mock_chain.data_source = "polygon"
    
    with patch('src.providers.eulerpool.EulerpoolProvider.health_check', return_value=True), \
         patch('src.providers.eulerpool.EulerpoolProvider.fetch_options_chain', side_effect=RateLimitError("Eulerpool rate limit")), \
         patch('src.providers.polygon.PolygonProvider.health_check', return_value=True), \
         patch('src.providers.polygon.PolygonProvider.fetch_options_chain', return_value=mock_chain):
        
        result = await router.fetch_chain("AAPL")
        assert result.data_source == "polygon"

@pytest.mark.asyncio
async def test_router_all_fail():
    router = ProviderRouter(["eulerpool"])
    
    with patch('src.providers.eulerpool.EulerpoolProvider.health_check', return_value=False):
        with pytest.raises(AllProvidersFailedError):
            await router.fetch_chain("AAPL")
