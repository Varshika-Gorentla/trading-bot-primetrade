"""
bot/orders.py
~~~~~~~~~~~~~
Order placement logic — the business layer of the bot.

This module translates validated parameters into Binance API payloads,
calls client.place_order(), and returns typed OrderResponse objects.

Interviewer talking point:
  "The orders module is the business layer. It builds the exact payload
   Binance expects from our clean internal parameters. Keeping this separate
   from the HTTP client means I can unit-test order-building logic without
   ever making a real network call."
"""

from __future__ import annotations

import time
from decimal import Decimal

from bot.client import BinanceClient
from bot.exceptions import TWAPError
from bot.logging_config import get_logger
from bot.models import OrderResponse, TWAPResult

logger = get_logger(__name__)


class OrderManager:
    """Handles all order-related operations."""

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    # ── Public order methods ──────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
    ) -> OrderResponse:
        """Place a MARKET order."""
        logger.info(
            "Building MARKET order",
            extra={"symbol": symbol, "side": side, "quantity": str(quantity)},
        )

        params = {
            "symbol":   symbol,
            "side":     side,
            "type":     "MARKET",
            "quantity": str(quantity),
        }

        raw = self._client.place_order(params)
        return OrderResponse.from_api(raw)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        time_in_force: str = "GTC",
    ) -> OrderResponse:
        """Place a LIMIT order."""
        logger.info(
            "Building LIMIT order",
            extra={
                "symbol": symbol,
                "side": side,
                "quantity": str(quantity),
                "price": str(price),
                "tif": time_in_force,
            },
        )

        params = {
            "symbol":      symbol,
            "side":        side,
            "type":        "LIMIT",
            "quantity":    str(quantity),
            "price":       str(price),
            "timeInForce": time_in_force,
        }

        raw = self._client.place_order(params)
        return OrderResponse.from_api(raw)

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        stop_price: Decimal,
    ) -> OrderResponse:
        """Place a STOP_LIMIT order."""
        logger.info(
            "Building STOP_LIMIT order",
            extra={
                "symbol": symbol, "side": side,
                "quantity": str(quantity),
                "price": str(price), "stop_price": str(stop_price),
            },
        )

        params = {
            "symbol":      symbol,
            "side":        side,
            "type":        "STOP",
            "quantity":    str(quantity),
            "price":       str(price),
            "stopPrice":   str(stop_price),
            "timeInForce": "GTC",
        }

        raw = self._client.place_order(params)
        return OrderResponse.from_api(raw)

    # ── BONUS: TWAP execution ─────────────────────────────────────────────────

    def execute_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: Decimal,
        slices: int,
        interval_seconds: int,
        dry_run: bool = False,
    ) -> TWAPResult:
        """Execute a TWAP strategy.

        Splits total_quantity into equal market orders placed
        every interval_seconds seconds.

        TWAP reduces market impact — a large single order would move
        the price against you, but spreading it over time minimises
        slippage. This is the core concept behind institutional
        algorithmic trading.
        """
        slice_qty = (total_quantity / slices).quantize(Decimal("0.001"))
        result = TWAPResult(
            symbol=symbol,
            side=side,
            total_qty=float(total_quantity),
            slices=slices,
            completed_slices=0,
            failed_slices=0,
        )

        logger.info(
            "TWAP execution started",
            extra={
                "symbol": symbol, "side": side,
                "total_qty": str(total_quantity),
                "slices": slices, "slice_qty": str(slice_qty),
                "interval_seconds": interval_seconds,
                "dry_run": dry_run,
            },
        )

        for i in range(1, slices + 1):
            logger.info(
                f"TWAP slice {i}/{slices}",
                extra={"slice_qty": str(slice_qty), "dry_run": dry_run},
            )

            if not dry_run:
                try:
                    order = self.place_market_order(symbol, side, slice_qty)
                    result.orders.append(order)
                    result.completed_slices += 1
                    result.total_executed_qty += float(order.executed_qty)
                    logger.info(
                        f"TWAP slice {i} filled",
                        extra={"orderId": order.order_id, "avgPrice": order.avg_price},
                    )
                except Exception as exc:
                    result.failed_slices += 1
                    logger.error(
                        f"TWAP slice {i} failed",
                        extra={"error": str(exc)},
                        exc_info=True,
                    )
            else:
                result.completed_slices += 1
                result.total_executed_qty += float(slice_qty)
                logger.info(f"[DRY RUN] TWAP slice {i} simulated")

            if i < slices:
                logger.debug(f"TWAP waiting {interval_seconds}s before next slice")
                time.sleep(interval_seconds)

        if result.orders:
            filled_prices = [
                float(o.avg_price) for o in result.orders if float(o.avg_price) > 0
            ]
            if filled_prices:
                result.avg_fill_price = sum(filled_prices) / len(filled_prices)

        logger.info(
            "TWAP execution complete",
            extra={
                "completed": result.completed_slices,
                "failed": result.failed_slices,
                "total_executed_qty": result.total_executed_qty,
                "avg_fill_price": result.avg_fill_price,
            },
        )

        if result.failed_slices == slices:
            raise TWAPError(f"All {slices} TWAP slices failed. Check logs for details.")

        return result