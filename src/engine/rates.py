import logging
from typing import Tuple

logger = logging.getLogger(__name__)

async def get_rates() -> Tuple[float, float]:
    """
    Returns (risk_free_rate, dividend_yield).
    Attempts to fetch risk free rate dynamically. 
    Uses a standard estimation for SPX dividend yield.
    """
    risk_free_rate = 0.05  # fallback 5%
    dividend_yield = 0.013 # SPX historically around 1.3 - 1.5%

    try:
        import yfinance as yf
        # ^IRX is the 13-week Treasury Bill index, which represents the risk-free rate
        irx = yf.Ticker("^IRX")
        hist = irx.history(period="1d")
        if not hist.empty:
            rate_pct = hist['Close'].iloc[-1]
            risk_free_rate = float(rate_pct) / 100.0
            logger.info(f"Dynamically fetched risk-free rate: {risk_free_rate:.4f}")
    except Exception as e:
        logger.warning(f"Could not fetch dynamic risk-free rate, using fallback. Error: {e}")

    return risk_free_rate, dividend_yield
