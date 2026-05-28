import logging
import numpy as np
from datetime import datetime

from ..models.options import OptionsChain, GEXResult
from .black_scholes import vectorized_gamma, vectorized_gamma_profile
from .rates import get_rates

logger = logging.getLogger(__name__)

async def calculate_gex(chain: OptionsChain) -> GEXResult:
    start_time = datetime.now()
    
    r, q = await get_rates()
    spot_price = chain.spot_price

    if not spot_price or spot_price <= 0:
        raise ValueError("Spot price must be > 0 to calculate GEX")

    # Filter out contracts with 0 open interest or expiration in the past
    valid_contracts = [c for c in chain.contracts if c.open_interest > 0 and c.expiration >= start_time.date()]
    if not valid_contracts:
        raise ValueError("No valid contracts with open interest to calculate GEX")

    # Extract arrays for vectorization
    n = len(valid_contracts)
    strikes = np.zeros(n)
    T = np.zeros(n)
    vol = np.zeros(n)
    oi = np.zeros(n)
    contract_types = np.zeros(n) # 1 for call, -1 for put
    gammas = np.zeros(n)
    needs_gamma = []

    for i, c in enumerate(valid_contracts):
        strikes[i] = c.strike
        days_to_exp = (c.expiration - start_time.date()).days
        # Convert to years (using 365 for calendar days, or could use 252 for trading days)
        T[i] = max(days_to_exp / 365.0, 1e-5) 
        vol[i] = c.implied_volatility
        oi[i] = c.open_interest
        contract_types[i] = 1 if c.contract_type == 'call' else -1
        
        if c.gamma is not None and c.gamma != 0:
            gammas[i] = c.gamma
        else:
            needs_gamma.append(i)

    # Calculate missing gammas using Black-Scholes
    if needs_gamma:
        idx = np.array(needs_gamma)
        calc_gammas = vectorized_gamma(
            spot=spot_price,
            strikes=strikes[idx],
            T=T[idx],
            vol=vol[idx],
            r=r,
            q=q
        )
        gammas[idx] = calc_gammas

    # Calculate GEX for current spot
    # GEX = Gamma * OI * 100 * Spot * (1 for call, -1 for put)
    # Some conventions use Spot^2 * 0.01. We'll use Spot * 100 which is equivalent in dollar terms.
    # Actually, SpotGamma convention: Gamma * OI * 100 * Spot * Spot * 0.01 ? 
    # Let's use the standard one: GEX = Gamma * OI * 100 * Spot * sign
    gex_values = gammas * oi * 100 * spot_price * contract_types
    
    total_gex_by_strike = {}
    call_gex_by_strike = {}
    put_gex_by_strike = {}

    for i in range(n):
        k = strikes[i]
        gex = float(gex_values[i])
        total_gex_by_strike[k] = total_gex_by_strike.get(k, 0.0) + gex
        if contract_types[i] == 1:
            call_gex_by_strike[k] = call_gex_by_strike.get(k, 0.0) + gex
        else:
            put_gex_by_strike[k] = put_gex_by_strike.get(k, 0.0) + gex

    # Calculate Gamma Profile & Gamma Flip
    levels, total_gamma = vectorized_gamma_profile(
        spot=spot_price,
        strikes=strikes,
        T=T,
        vol=vol,
        oi=oi,
        contract_types=contract_types,
        r=r,
        q=q
    )

    gamma_profile = {float(levels[i]): float(total_gamma[i]) for i in range(len(levels))}
    
    # Find Gamma Flip (zero crossing)
    gamma_flip = _find_gamma_flip(levels, total_gamma)

    elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

    return GEXResult(
        spot_price=spot_price,
        total_gex=total_gex_by_strike,
        call_gex=call_gex_by_strike,
        put_gex=put_gex_by_strike,
        gamma_flip=gamma_flip,
        gamma_profile=gamma_profile,
        computation_time_ms=elapsed_ms
    )

def _find_gamma_flip(levels: np.ndarray, total_gamma: np.ndarray) -> float | None:
    sign_changes = np.where(np.diff(np.sign(total_gamma)))[0]
    if len(sign_changes) == 0:
        return None
    
    # Linear interpolation for better precision
    idx = sign_changes[0]
    x1, x2 = levels[idx], levels[idx + 1]
    y1, y2 = total_gamma[idx], total_gamma[idx + 1]
    
    # Check for divide by zero just in case
    if y2 - y1 == 0:
        return float(x1)
        
    gamma_flip = x1 - y1 * (x2 - x1) / (y2 - y1)
    return float(gamma_flip)
