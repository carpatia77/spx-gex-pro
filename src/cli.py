import asyncio
import logging
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.logging import RichHandler

from .config import settings
from .providers.router import get_router
from .engine.gex import calculate_gex
from .visualization.charts import plot_gex_dashboard

# Setup logging
logging.basicConfig(
    level="WARNING",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)

logger = logging.getLogger("spx_gex")
app = typer.Typer(help="SPX500 Gamma Exposure (GEX) Calculator")
console = Console()


async def async_run(ticker: str, verbose: bool, output: str):
    if verbose:
        logger.setLevel("INFO")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            
            task = progress.add_task(description=f"Initializing providers...", total=None)
            
            # 1. Init router
            router = get_router(settings.provider_order)
            
            # 2. Fetch data
            progress.update(task, description=f"Fetching options chain for {ticker}...")
            chain = await router.fetch_chain(ticker)
            
            # 3. Calculate GEX
            progress.update(task, description=f"Calculating Gamma Exposure (vectorized)...")
            gex_result = await calculate_gex(chain)
            
            # 4. Visualization
            progress.update(task, description=f"Generating dashboard...")
            out_path = settings.output_dir
            if output:
                out_path = Path(output)
            
            chart_path = plot_gex_dashboard(gex_result, ticker, out_path)
            
        # Display Results
        console.print(f"\n[bold green]Successfully calculated GEX for {ticker}[/bold green]")
        console.print(f"Data Source: [cyan]{chain.data_source}[/cyan] | Contracts: [cyan]{len(chain.contracts)}[/cyan]")
        console.print(f"Calculation Time: [yellow]{gex_result.computation_time_ms:.2f}ms[/yellow]\n")
        
        # Summary Table
        table = Table(title=f"{ticker} Gamma Exposure Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Spot Price", f"{gex_result.spot_price:.2f}")
        
        if gex_result.gamma_flip:
            table.add_row("Gamma Flip (Zero GEX)", f"{gex_result.gamma_flip:.2f}")
        else:
            table.add_row("Gamma Flip (Zero GEX)", "N/A")
            
        # Calculate Total Absolute GEX
        total_gex_bn = sum(gex_result.total_gex.values()) / 1e9
        table.add_row("Net GEX (Billions)", f"${total_gex_bn:,.2f}B")
        
        console.print(table)
        console.print(f"\n[bold]Dashboard saved to:[/bold] {chart_path.absolute()}")

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if verbose:
            logger.exception("Detailed error traceback:")
        raise typer.Exit(code=1)


@app.command()
def run(
    ticker: str = typer.Argument("SPX", help="Ticker symbol (e.g., SPX, AAPL)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    output: str = typer.Option(None, "--output", "-o", help="Custom output directory for charts"),
):
    """
    Run the GEX calculator for a given ticker.
    """
    asyncio.run(async_run(ticker, verbose, output))


if __name__ == "__main__":
    app()
