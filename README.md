# SPX GEX Pro — Professional Gamma Exposure Calculator

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Data-Eulerpool%20%7C%20Polygon%20%7C%20Yahoo-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Math-NumPy%20%7C%20SciPy-orange?style=for-the-badge&logo=numpy" />
</p>

> **Professional-grade Gamma Exposure (GEX) analysis tool for the S&P 500 and US equities.**
> Built with API routing, vectorized Black-Scholes mathematics, and an automated quota-aware cache system.

---

## 📊 What is Gamma Exposure (GEX)?

Gamma Exposure measures how much **options market makers must hedge** in the underlying asset for every 1% move in price. It is one of the most important derivatives-based signals in quantitative finance:

| GEX Regime | Market Behaviour |
|---|---|
| **Positive GEX** *(above Gamma Flip)* | Market makers buy dips & sell rallies → **mean-reverting, low-vol market** |
| **Negative GEX** *(below Gamma Flip)* | Market makers amplify moves in both directions → **trending, high-vol market** |

The **Gamma Flip** (zero-GEX level) is the critical price boundary that separates these two regimes.

---

## ✨ Features

- 🔄 **Smart API Routing** — Cascading fallback across 3 providers: **Eulerpool → Polygon.io → Yahoo Finance**
- ⚡ **Vectorized Black-Scholes** — Evaluates Greeks for thousands of contracts simultaneously using `NumPy`/`SciPy` (no slow Python loops)
- 💾 **Quota-Aware Cache** — Local disk cache (1-hour TTL by default) protects monthly API limits from being exhausted on repeated runs
- 📈 **Dynamic Risk-Free Rate** — Automatically fetches the 13-week US Treasury yield (`^IRX`) for mathematically rigorous pricing
- 🎨 **Rich GEX Dashboard** — 4-panel chart exported as high-resolution PNG:
  - Total Absolute GEX by Strike
  - Call GEX vs Put GEX
  - Market Maker Gamma Profile (full price range simulation)
  - Gamma Flip level marked with precision interpolation
- 🖥️ **Professional CLI** — Powered by `Typer` and `Rich` with live progress indicators and a summary table

---

## 🏗️ Architecture

```
spx-gex-pro/
├── src/
│   ├── config.py                  # Settings via pydantic-settings + .env
│   ├── cli.py                     # Typer CLI application
│   ├── __main__.py                # python -m src entrypoint
│   │
│   ├── models/
│   │   └── options.py             # Typed dataclasses: OptionContract, OptionsChain, GEXResult
│   │
│   ├── providers/                 # API Routing Layer
│   │   ├── base.py                # AbstractProvider ABC
│   │   ├── eulerpool.py           # Primary: Eulerpool (ISIN-based, Greeks included)
│   │   ├── polygon.py             # Fallback 1: Polygon.io (real-time Greeks)
│   │   ├── yahoo.py               # Fallback 2: yfinance (free, no Greeks)
│   │   └── router.py             # ProviderRouter — cascading failover logic
│   │
│   ├── engine/                    # Calculation Engine
│   │   ├── black_scholes.py       # Vectorized gamma + gamma profile (2D broadcasting)
│   │   ├── gex.py                 # GEX orchestrator: builds GEXResult from OptionsChain
│   │   └── rates.py               # Dynamic risk-free rate + dividend yield
│   │
│   └── visualization/
│       └── charts.py              # 4-panel Matplotlib GEX dashboard
│
├── tests/
│   └── test_router.py             # Unit tests for routing and fallback logic
│
├── output/                        # Generated charts (git-ignored)
├── .cache/                        # API response cache (git-ignored)
├── .env.example                   # Template for environment variables
└── pyproject.toml                 # Project metadata and dependencies
```

---

## 🚀 Quickstart

### 1. Clone the repository

```bash
git clone https://github.com/carpatia77/spx-gex-pro.git
cd spx-gex-pro
```

### 2. Configure your API keys

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```dotenv
# Required for primary data source
EULERPOOL_API_KEY=your_eulerpool_api_key_here

# Optional — enables Polygon as the first fallback
POLYGON_API_KEY=your_polygon_api_key_here
```

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

### 3. Install dependencies

```bash
pip install .
```

Or with `uv` (faster):

```bash
uv pip install .
```

### 4. Run

```bash
# Calculate GEX for the S&P 500
python -m src SPX

# Calculate GEX for Apple
python -m src AAPL

# Enable verbose logging and save charts to a custom folder
python -m src SPX --verbose --output ./charts
```

---

## ⚙️ Configuration

All settings are managed via `.env` and can be overridden as environment variables:

| Variable | Default | Description |
|---|---|---|
| `EULERPOOL_API_KEY` | *None* | Eulerpool API key (primary provider) |
| `POLYGON_API_KEY` | *None* | Polygon.io API key (fallback 1) |
| `DEFAULT_TICKER` | `SPX` | Default ticker symbol |
| `STRIKE_RANGE_PCT` | `0.20` | Strike filter: ±20% around spot price |
| `CACHE_TTL_SECONDS` | `3600` | Cache time-to-live (1 hour) |
| `CHART_THEME` | `dark` | Chart theme: `dark` or `light` |
| `PROVIDER_ORDER` | `["eulerpool","polygon","yahoo"]` | Provider priority list |

---

## 📡 Provider Routing

```
Request
   │
   ▼
[Eulerpool] ──✓──► Return chain (Greeks included)
   │ ✗ (RateLimit / Error)
   ▼
[Polygon.io] ──✓──► Return chain (Greeks included)
   │ ✗ (not configured / error)
   ▼
[Yahoo Finance] ──✓──► Return chain (GEX engine computes Greeks via B-S)
   │ ✗
   ▼
AllProvidersFailedError
```

The router **marks unhealthy providers** for the duration of the session, avoiding redundant failing calls.

---

## 🧮 Mathematics

### Black-Scholes Gamma

```
         N'(d1)
Γ = ──────────────────
      S · σ · √T
```

Where `d1 = [ln(F/K) + 0.5σ²T] / (σ√T)` and `F = S·e^(r-q)T` is the forward price.

### Dollar Gamma Exposure

```
GEX(K) = Γ · OI · 100 · S · sign(contract_type)
```

- `sign` is **+1 for calls** (dealers are long gamma) and **−1 for puts** (dealers are short gamma)
- The **Gamma Profile** is computed by re-evaluating the above across a price grid `[0.8S, 1.2S]` using 2D NumPy broadcasting

---

## 🧪 Running Tests

```bash
pip install .[dev]
pytest tests/ -v
```

---

## 🗺️ Roadmap

- [ ] Interactive HTML charts (Plotly) via `--format html`
- [ ] Multi-expiration breakdown (e.g., 0DTE vs weekly vs monthly)
- [ ] Historical GEX series export to CSV
- [ ] Polygon historical fallback for post-market analysis

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Eulerpool](https://eulerpool.com) — Primary options data source
- [Polygon.io](https://polygon.io) — Institutional-grade market data
- [SpotGamma](https://spotgamma.com) — Inspiration for GEX methodology and visualization
