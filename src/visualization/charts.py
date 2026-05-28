import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from pathlib import Path

from ..models.options import GEXResult
from ..config import settings

def plot_gex_dashboard(gex_result: GEXResult, ticker_name: str, output_path: Path) -> Path:
    """
    Creates a unified 2x2 dashboard of GEX charts.
    Returns the path to the saved image.
    """
    if settings.chart_theme == "dark":
        plt.style.use('dark_background')
        bg_color = '#0a0a0a'
        text_color = '#ffffff'
        grid_color = '#333333'
    else:
        plt.style.use('default')
        bg_color = '#ffffff'
        text_color = '#000000'
        grid_color = '#e0e0e0'

    fig = plt.figure(figsize=(18, 12), facecolor=bg_color)
    fig.suptitle(f"{ticker_name} Gamma Exposure (GEX) Dashboard - Spot: {gex_result.spot_price:.2f}", 
                 fontsize=18, color=text_color, y=0.95)

    # Convert dicts to sorted arrays
    strikes = np.array(sorted(gex_result.total_gex.keys()))
    total_gex = np.array([gex_result.total_gex[k] for k in strikes]) / 1e9  # In billions
    call_gex = np.array([gex_result.call_gex.get(k, 0) for k in strikes]) / 1e9
    put_gex = np.array([gex_result.put_gex.get(k, 0) for k in strikes]) / 1e9

    # Filter to strikes within strike_range_pct of spot
    lower_bound = gex_result.spot_price * (1 - settings.strike_range_pct)
    upper_bound = gex_result.spot_price * (1 + settings.strike_range_pct)
    
    mask = (strikes >= lower_bound) & (strikes <= upper_bound)
    strikes_filtered = strikes[mask]
    total_gex_filtered = total_gex[mask]
    call_gex_filtered = call_gex[mask]
    put_gex_filtered = put_gex[mask]

    # --- Plot 1: Absolute GEX by Strike ---
    ax1 = plt.subplot(2, 2, 1)
    ax1.set_facecolor(bg_color)
    colors1 = ['green' if g > 0 else 'red' for g in total_gex_filtered]
    ax1.bar(strikes_filtered, total_gex_filtered, width=max(1, (strikes_filtered[-1] - strikes_filtered[0])/len(strikes_filtered)*0.8), color=colors1)
    ax1.axvline(x=gex_result.spot_price, color='blue', linestyle='--', linewidth=2, label=f"Spot: {gex_result.spot_price:.0f}")
    if gex_result.gamma_flip:
        ax1.axvline(x=gex_result.gamma_flip, color='gold', linestyle='--', linewidth=2, label=f"Flip: {gex_result.gamma_flip:.0f}")
    
    ax1.set_title("Total Gamma Exposure (GEX) by Strike", color=text_color)
    ax1.set_ylabel("GEX (Billions $ per 1% move)", color=text_color)
    ax1.grid(color=grid_color, linestyle=':', alpha=0.6)
    ax1.legend(facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color)

    # --- Plot 2: Call GEX vs Put GEX ---
    ax2 = plt.subplot(2, 2, 2)
    ax2.set_facecolor(bg_color)
    width = max(1, (strikes_filtered[-1] - strikes_filtered[0])/len(strikes_filtered)*0.4)
    ax2.bar(strikes_filtered - width/2, call_gex_filtered, width=width, color='#00ff00', label='Call GEX', alpha=0.7)
    ax2.bar(strikes_filtered + width/2, put_gex_filtered, width=width, color='#ff0000', label='Put GEX', alpha=0.7)
    ax2.axvline(x=gex_result.spot_price, color='blue', linestyle='--', linewidth=2)
    
    ax2.set_title("Call vs Put GEX by Strike", color=text_color)
    ax2.set_ylabel("GEX (Billions $)", color=text_color)
    ax2.grid(color=grid_color, linestyle=':', alpha=0.6)
    ax2.legend(facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color)

    # --- Plot 3: Gamma Profile ---
    ax3 = plt.subplot(2, 1, 2)
    ax3.set_facecolor(bg_color)
    
    levels = np.array(sorted(gex_result.gamma_profile.keys()))
    profile = np.array([gex_result.gamma_profile[k] for k in levels]) / 1e9
    
    ax3.plot(levels, profile, color='white' if settings.chart_theme == 'dark' else 'black', linewidth=2)
    ax3.fill_between(levels, profile, 0, where=(profile >= 0), color='green', alpha=0.3)
    ax3.fill_between(levels, profile, 0, where=(profile < 0), color='red', alpha=0.3)
    
    ax3.axhline(y=0, color=grid_color, linestyle='-')
    ax3.axvline(x=gex_result.spot_price, color='blue', linestyle='--', linewidth=2, label=f"Spot: {gex_result.spot_price:.0f}")
    
    if gex_result.gamma_flip:
        ax3.axvline(x=gex_result.gamma_flip, color='gold', linestyle='--', linewidth=2, label=f"Flip: {gex_result.gamma_flip:.0f}")
        ax3.plot(gex_result.gamma_flip, 0, marker='o', markersize=10, color='gold')

    ax3.set_title("Market Maker Gamma Profile (Simulated Spot Moves)", color=text_color)
    ax3.set_xlabel("Spot Price", color=text_color)
    ax3.set_ylabel("Total GEX (Billions $)", color=text_color)
    ax3.grid(color=grid_color, linestyle=':', alpha=0.6)
    ax3.legend(facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color)

    # Add performance watermark
    fig.text(0.99, 0.01, f"Computed in {gex_result.computation_time_ms:.1f}ms", 
             ha='right', va='bottom', fontsize=10, color=grid_color)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    filepath = output_path / f"{ticker_name}_GEX_Dashboard.png"
    plt.savefig(filepath, dpi=300, facecolor=bg_color, edgecolor='none')
    plt.close()
    
    return filepath
