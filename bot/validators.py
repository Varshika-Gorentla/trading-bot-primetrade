"""
bot/validators.py
~~~~~~~~~~~~~~~~~
All input validation lives here — nothing else validates anything.

"Parse, don't validate" principle: validators return clean, typed values
(not just True/False) so the caller gets usable data from the start.

Interviewer talking point:
  "I applied the 'parse, don't validate' principle — validators return
   normalised, typed values. This means once data passes the validator, the
   rest of the code never needs to check the format again."
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from bot.exceptions import (
    InvalidOrderTypeError,
    InvalidPriceError,
    InvalidQuantityError,
    InvalidSideError,
    InvalidSymbolError,
    MissingPriceError,
)

# ── Allowed values ────────────────────────────────────────────────────────────

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

SYMBOL_RE = re.compile(r"^[A-Z]{2,10}(USDT|BUSD|BTC|ETH|BNB)$")

MIN_QUANTITY = Decimal("0.00001")
MAX_QUANTITY = Decimal("1_000_000")

MIN_PRICE = Decimal("0.00001")
MAX_PRICE = Decimal("10_000_000")


# ── Individual validators ─────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """Return uppercased symbol or raise InvalidSymbolError."""
    cleaned = symbol.strip().upper()
    if not SYMBOL_RE.match(cleaned):
        raise InvalidSymbolError(
            f"'{symbol}' is not a valid Binance futures symbol. "
            f"Examples: BTCUSDT, ETHUSDT, BNBUSDT"
        )
    return cleaned


def validate_side(side: str) -> str:
    """Return uppercased side or raise InvalidSideError."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise InvalidSideError(
            f"Side must be BUY or SELL, got '{side}'."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise InvalidOrderTypeError."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise InvalidOrderTypeError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}, got '{order_type}'."
        )
    return cleaned


def validate_quantity(quantity: str | float) -> Decimal:
    """Return a Decimal quantity or raise InvalidQuantityError."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise InvalidQuantityError(
            f"Quantity must be a number, got '{quantity}'."
        )

    if qty <= 0:
        raise InvalidQuantityError("Quantity must be greater than zero.")
    if qty < MIN_QUANTITY:
        raise InvalidQuantityError(
            f"Quantity {qty} is below the minimum allowed ({MIN_QUANTITY})."
        )
    if qty > MAX_QUANTITY:
        raise InvalidQuantityError(
            f"Quantity {qty} exceeds the maximum allowed ({MAX_QUANTITY})."
        )
    return qty


def validate_price(price: str | float | None, *, required: bool = False) -> Decimal | None:
    """Return a Decimal price, None if not provided, or raise on invalid input."""
    if price is None or str(price).strip() == "":
        if required:
            raise MissingPriceError(
                "Price is required for LIMIT orders. Use --price <value>."
            )
        return None

    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise InvalidPriceError(
            f"Price must be a number, got '{price}'."
        )

    if p <= 0:
        raise InvalidPriceError("Price must be greater than zero.")
    if p < MIN_PRICE:
        raise InvalidPriceError(
            f"Price {p} is below the minimum allowed ({MIN_PRICE})."
        )
    if p > MAX_PRICE:
        raise InvalidPriceError(
            f"Price {p} exceeds the sanity cap ({MAX_PRICE}). "
            "Did you accidentally enter quantity instead of price?"
        )
    return p


def validate_stop_price(stop_price: str | float | None) -> Decimal | None:
    """Validate stop price for STOP_LIMIT orders."""
    return validate_price(stop_price, required=False)


# ── Composite validator ───────────────────────────────────────────────────────

def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
    stop_price: str | float | None = None,
) -> dict:
    """Run all validators and return a clean parameter dict."""
    order_type_clean = validate_order_type(order_type)

    return {
        "symbol":      validate_symbol(symbol),
        "side":        validate_side(side),
        "order_type":  order_type_clean,
        "quantity":    validate_quantity(quantity),
        "price":       validate_price(
                           price,
                           required=(order_type_clean in {"LIMIT", "STOP_LIMIT"})
                       ),
        "stop_price":  validate_stop_price(stop_price),
    }