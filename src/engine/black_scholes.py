import numpy as np
from scipy.stats import norm

def vectorized_gamma(
    spot: float,
    strikes: np.ndarray,      
    T: np.ndarray,             
    vol: np.ndarray,           
    r: float = 0.05,           
    q: float = 0.013,          
) -> np.ndarray:
    """
    Calculates gamma for N contracts in a single operation.
    """
    # Prevent division by zero
    T = np.maximum(T, 1e-5)
    vol = np.maximum(vol, 1e-5)
    
    # Forward price adjustment (European options)
    forward = spot * np.exp((r - q) * T)
    
    d1 = (np.log(forward / strikes) + 0.5 * vol**2 * T) / (vol * np.sqrt(T))
    gamma = norm.pdf(d1) / (spot * vol * np.sqrt(T))
    return gamma


def vectorized_gamma_profile(
    spot: float,
    strikes: np.ndarray,       
    T: np.ndarray,             
    vol: np.ndarray,           
    oi: np.ndarray,            
    contract_types: np.ndarray,
    n_levels: int = 60,
    r: float = 0.05,
    q: float = 0.013,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calculates the complete gamma profile with 2D broadcasting.
    """
    T = np.maximum(T, 1e-5)
    vol = np.maximum(vol, 1e-5)
    
    levels = np.linspace(0.8 * spot, 1.2 * spot, n_levels)
    
    # Broadcasting: levels (M,1) x strikes (1,N) -> (M,N) matrix
    levels_2d = levels[:, np.newaxis]
    strikes_2d = strikes[np.newaxis, :]
    T_2d = T[np.newaxis, :]
    vol_2d = vol[np.newaxis, :]
    
    forward_2d = levels_2d * np.exp((r - q) * T_2d)
    d1 = (np.log(forward_2d / strikes_2d) + 0.5 * vol_2d**2 * T_2d) / (vol_2d * np.sqrt(T_2d))
    gamma_2d = norm.pdf(d1) / (levels_2d * vol_2d * np.sqrt(T_2d))
    
    # GEX for each level: gamma * OI * 100 * level * sign
    # sign is 1 for call, -1 for put
    gex_2d = gamma_2d * oi[np.newaxis, :] * 100 * levels_2d * contract_types[np.newaxis, :]
    
    total_gamma = gex_2d.sum(axis=1)  # shape (M,)
    return levels, total_gamma
