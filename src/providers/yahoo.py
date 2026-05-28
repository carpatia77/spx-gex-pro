from datetime import date, datetime
from typing import Optional
import httpx

from ..config import settings
from ..models.options import OptionsChain, OptionContract
from .base import AbstractProvider, ProviderError, RateLimitError

class YahooProvider(AbstractProvider):
    def __init__(self):
        try:
            import yfinance as yf
            self.yf = yf
        except ImportError:
            self.yf = None

    @property
    def name(self) -> str:
        return "yahoo"

    @property
    def provides_greeks(self) -> bool:
        return False  # Yahoo only provides OI and IV, we must calculate Greeks

    async def health_check(self) -> bool:
        return self.yf is not None

    async def fetch_options_chain(
        self,
        ticker: str,
        expiration_range: Optional[tuple[date, date]] = None,
        strike_range: Optional[tuple[float, float]] = None,
    ) -> OptionsChain:
        if not self.yf:
            raise ProviderError("yfinance is not installed")

        # ^SPX is the Yahoo ticker for S&P 500
        yf_ticker = "^SPX" if ticker.upper() == "SPX" else ticker
        tk = self.yf.Ticker(yf_ticker)
        
        try:
            expirations = tk.options
            spot_price = tk.history(period="1d")['Close'].iloc[-1]
        except Exception as e:
            raise ProviderError(f"Failed to fetch data from Yahoo: {e}")

        contracts = []
        for exp_str in expirations:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
            if expiration_range and (exp_date < expiration_range[0] or exp_date > expiration_range[1]):
                continue

            try:
                opt = tk.option_chain(exp_str)
            except Exception:
                continue
            
            # Process calls
            for _, row in opt.calls.iterrows():
                strike = float(row['strike'])
                if strike_range and (strike < strike_range[0] or strike > strike_range[1]):
                    continue
                
                contracts.append(OptionContract(
                    strike=strike,
                    expiration=exp_date,
                    contract_type="call",
                    open_interest=int(row['openInterest']) if not type(row['openInterest']) is float or not row['openInterest'] != row['openInterest'] else 0,
                    implied_volatility=float(row['impliedVolatility'])
                ))
            
            # Process puts
            for _, row in opt.puts.iterrows():
                strike = float(row['strike'])
                if strike_range and (strike < strike_range[0] or strike > strike_range[1]):
                    continue
                
                contracts.append(OptionContract(
                    strike=strike,
                    expiration=exp_date,
                    contract_type="put",
                    open_interest=int(row['openInterest']) if not type(row['openInterest']) is float or not row['openInterest'] != row['openInterest'] else 0,
                    implied_volatility=float(row['impliedVolatility'])
                ))

        return OptionsChain(
            underlying_ticker=ticker,
            spot_price=float(spot_price),
            timestamp=datetime.now(),
            contracts=contracts,
            data_source=self.name
        )
