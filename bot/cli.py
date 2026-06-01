"""
bot/cli.py
~~~~~~~~~~
CLI entry point — all Typer commands live here.

The CLI layer's ONLY jobs are:
  1. Accept and parse user input
  2. Call validators
  3. Call the orders layer
  4. Format and print results
  5. Exit with the right code (0 = success, 1 = user error, 2 = API error)

Interviewer talking point:
  "The CLI is the thinnest possible layer. It translates user intent into
   function calls, then formats the response. Every heavy-lifting module
   can be imported and used programmatically or tested independently."
"""

from __future__ import annotations

import os
import sys
from decimal import Decimal
from typing import Optional

import typer
from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bot.client import BinanceClient
from bot.exceptions import TradingBotError, ValidationError
from bot.logging_config import get_logger, setup_logging
from bot.models import OrderResponse, TWAPResult
from bot.orders import OrderManager
from bot.validators import validate_order_params

# ── Initialise ────────────────────────────────────────────────────────────────

load_dotenv()
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = get_logger(__name__)

app = typer.Typer(
    name="trading-bot",
    help="Binance Futures Testnet Trading Bot",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()
err_console = Console(stderr=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client() -> BinanceClient:
    """Build a BinanceClient from environment variables."""
    api_key    = os.getenv("BINANCE_API_KEY", "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")
    return BinanceClient(api_key=api_key, api_secret=api_secret)


def _print_order_request(params: dict) -> None:
    """Print a summary of the order being placed."""
    table = Table(title="Order Request", box=box.ROUNDED, style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    field_map = {
        "symbol":     "Symbol",
        "side":       "Side",
        "order_type": "Order Type",
        "quantity":   "Quantity",
        "price":      "Limit Price",
        "stop_price": "Stop Price",
    }
    for key, label in field_map.items():
        value = params.get(key)
        if value is None:
            continue
        style = "green" if str(value) == "BUY" else "red" if str(value) == "SELL" else ""
        table.add_row(label, Text(str(value), style=style))

    console.print(table)


def _print_order_response(order: OrderResponse) -> None:
    """Print a formatted order response."""
    colour = "green" if order.is_filled else "yellow"

    table = Table(title="Order Response", box=box.ROUNDED, style=colour)
    table.add_column("Field", style="bold")
    table.add_column("Value")

    rows = [
        ("Order ID",         str(order.order_id)),
        ("Symbol",           order.symbol),
        ("Side",             order.side),
        ("Type",             order.order_type),
        ("Status",           order.status),
        ("Requested Qty",    order.orig_qty),
        ("Executed Qty",     order.executed_qty),
        ("Fill Price",       order.display_price),
        ("Cumulative Quote", f"{order.cum_quote} USDT"),
        ("Client Order ID",  order.client_order_id),
    ]
    for label, value in rows:
        table.add_row(label, value)

    console.print(table)

    if order.is_filled:
        console.print(Panel(
            f"[bold green]Order FILLED — {order.executed_qty} {order.symbol} @ {order.display_price}[/]",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold yellow]Order {order.status} — ID {order.order_id}[/]",
            border_style="yellow",
        ))


def _print_twap_result(result: TWAPResult) -> None:
    """Print a TWAP execution summary."""
    table = Table(title="TWAP Execution Summary", box=box.ROUNDED, style="magenta")
    table.add_column("Field", style="bold")
    table.add_column("Value")

    table.add_row("Symbol",           result.symbol)
    table.add_row("Side",             result.side)
    table.add_row("Total Quantity",   str(result.total_qty))
    table.add_row("Slices",           str(result.slices))
    table.add_row("Completed Slices", str(result.completed_slices))
    table.add_row("Failed Slices",    str(result.failed_slices))
    table.add_row("Total Executed",   f"{result.total_executed_qty:.6f}")
    table.add_row("Avg Fill Price",   f"{result.avg_fill_price:.4f}" if result.avg_fill_price else "N/A")
    table.add_row("Success Rate",     f"{result.success_rate:.1f}%")

    console.print(table)


def _abort(message: str, code: int = 1) -> None:
    """Print error panel and exit."""
    err_console.print(Panel(f"[bold red]ERROR: {message}[/]", border_style="red"))
    logger.error("Aborted", extra={"reason": message})
    raise typer.Exit(code=code)


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command()
def order(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", "-d", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET | LIMIT | STOP_LIMIT"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Order size"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Limit price"),
    stop_price: Optional[float] = typer.Option(None, "--stop-price", help="Stop trigger price"),
    time_in_force: str = typer.Option("GTC", "--tif", help="GTC | IOC | FOK"),
) -> None:
    """Place a single order on Binance Futures Testnet."""

    console.print(Panel(
        "[bold cyan]Binance Futures Testnet — Order Placement[/]",
        border_style="cyan",
    ))

    try:
        params = validate_order_params(
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price, stop_price=stop_price,
        )
    except ValidationError as exc:
        _abort(str(exc))

    _print_order_request(params)

    try:
        with _get_client() as client:
            manager = OrderManager(client)

            if params["order_type"] == "MARKET":
                result = manager.place_market_order(
                    symbol=params["symbol"],
                    side=params["side"],
                    quantity=params["quantity"],
                )
            elif params["order_type"] == "LIMIT":
                result = manager.place_limit_order(
                    symbol=params["symbol"],
                    side=params["side"],
                    quantity=params["quantity"],
                    price=params["price"],
                    time_in_force=time_in_force.upper(),
                )
            else:
                result = manager.place_stop_limit_order(
                    symbol=params["symbol"],
                    side=params["side"],
                    quantity=params["quantity"],
                    price=params["price"],
                    stop_price=params["stop_price"],
                )

    except TradingBotError as exc:
        logger.error("Order placement failed", exc_info=True)
        _abort(str(exc), code=2)
    except Exception as exc:
        logger.critical("Unexpected error", exc_info=True)
        _abort(f"Unexpected error: {exc}", code=2)

    _print_order_response(result)


@app.command()
def twap(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair e.g. BTCUSDT"),
    side: str = typer.Option(..., "--side", "-d", help="BUY or SELL"),
    quantity: float = typer.Option(..., "--quantity", "-q", help="Total quantity"),
    slices: int = typer.Option(5, "--slices", "-n", help="Number of child orders"),
    interval: int = typer.Option(60, "--interval", "-i", help="Seconds between slices"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate without placing real orders"),
) -> None:
    """Execute a TWAP strategy — split a large order into time-spaced slices."""

    console.print(Panel(
        f"[bold magenta]TWAP Execution Engine[/]\n"
        f"[dim]{slices} slices every {interval}s — total ~{slices * interval}s[/]",
        border_style="magenta",
    ))

    if dry_run:
        console.print("[bold yellow]DRY RUN mode — no real orders will be placed[/]")

    try:
        from bot.validators import validate_symbol, validate_side, validate_quantity
        sym = validate_symbol(symbol)
        sd  = validate_side(side)
        qty = validate_quantity(quantity)
    except ValidationError as exc:
        _abort(str(exc))

    if slices < 2:
        _abort("TWAP requires at least 2 slices.")
    if interval < 1:
        _abort("Interval must be at least 1 second.")

    try:
        with _get_client() as client:
            manager = OrderManager(client)
            result = manager.execute_twap(
                symbol=sym,
                side=sd,
                total_quantity=qty,
                slices=slices,
                interval_seconds=interval,
                dry_run=dry_run,
            )
    except TradingBotError as exc:
        logger.error("TWAP execution failed", exc_info=True)
        _abort(str(exc), code=2)

    _print_twap_result(result)


@app.command()
def ping() -> None:
    """Check connectivity to Binance Futures Testnet."""
    console.print("Checking testnet connectivity...")
    try:
        with _get_client() as client:
            ok = client.ping()
            server_time = client.get_server_time()
    except TradingBotError as exc:
        _abort(str(exc))

    if ok:
        console.print(Panel(
            f"[bold green]Testnet reachable[/]\n[dim]Server time: {server_time}[/]",
            border_style="green",
        ))
    else:
        _abort("Testnet unreachable — check your internet connection.", code=2)


@app.command()
def balance() -> None:
    """Show your testnet account balance."""
    console.print("Fetching account balance...")
    try:
        with _get_client() as client:
            account = client.get_account()
    except TradingBotError as exc:
        _abort(str(exc))

    assets = account.get("assets", [])
    table = Table(title="Account Balance", box=box.ROUNDED, style="green")
    table.add_column("Asset",          style="bold")
    table.add_column("Wallet Balance", justify="right")
    table.add_column("Available",      justify="right")
    table.add_column("Unrealised PnL", justify="right")

    for asset in assets:
        wallet = float(asset.get("walletBalance", 0))
        if wallet == 0:
            continue
        table.add_row(
            asset.get("asset", ""),
            f"{wallet:.4f}",
            f"{float(asset.get('availableBalance', 0)):.4f}",
            f"{float(asset.get('unrealizedProfit', 0)):.4f}",
        )

    console.print(table)


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()