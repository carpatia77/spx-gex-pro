from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

@dataclass
class OptionContract:
    strike: float
    expiration: date
    contract_type: Literal["call", "put"]
    open_interest: int
    implied_volatility: float
    # Greeks (optional - not all providers supply them)
    delta: float | None = None
    gamma: float | None = None
    theta: float | None = None
    vega: float | None = None

@dataclass
class OptionsChain:
    underlying_ticker: str
    spot_price: float
    timestamp: datetime
    contracts: list[OptionContract]
    data_source: str

@dataclass
class GEXResult:
    spot_price: float
    total_gex: dict[float, float]       # strike -> total GEX
    call_gex: dict[float, float]        # strike -> call GEX
    put_gex: dict[float, float]         # strike -> put GEX
    gamma_flip: float | None            # Zero gamma level
    gamma_profile: dict[float, float]   # price_level -> total_gamma
    computation_time_ms: float
