"""
tests/test_validators.py
~~~~~~~~~~~~~~~~~~~~~~~~
Unit tests for the validators module.

These tests run without any network calls — pure logic testing.
"""

import pytest
from decimal import Decimal
from bot.validators import (
    validate_symbol, validate_side, validate_order_type,
    validate_quantity, validate_price, validate_order_params,
)
from bot.exceptions import (
    InvalidSymbolError, InvalidSideError, InvalidOrderTypeError,
    InvalidQuantityError, InvalidPriceError, MissingPriceError,
)


class TestValidateSymbol:
    def test_valid_btcusdt(self):
        assert validate_symbol("BTCUSDT") == "BTCUSDT"

    def test_valid_lowercase(self):
        assert validate_symbol("ethusdt") == "ETHUSDT"

    def test_valid_with_whitespace(self):
        assert validate_symbol("  BTCUSDT  ") == "BTCUSDT"

    def test_invalid_random_string(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("FAKECOIN")

    def test_invalid_empty(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("")

    def test_invalid_number(self):
        with pytest.raises(InvalidSymbolError):
            validate_symbol("123456")


class TestValidateSide:
    def test_buy(self):
        assert validate_side("BUY") == "BUY"

    def test_sell_lowercase(self):
        assert validate_side("sell") == "SELL"

    def test_invalid(self):
        with pytest.raises(InvalidSideError):
            validate_side("LONG")


class TestValidateOrderType:
    def test_market(self):
        assert validate_order_type("MARKET") == "MARKET"

    def test_limit_lowercase(self):
        assert validate_order_type("limit") == "LIMIT"

    def test_stop_limit(self):
        assert validate_order_type("STOP_LIMIT") == "STOP_LIMIT"

    def test_invalid(self):
        with pytest.raises(InvalidOrderTypeError):
            validate_order_type("TWAP")


class TestValidateQuantity:
    def test_valid(self):
        assert validate_quantity("0.001") == Decimal("0.001")

    def test_valid_float(self):
        assert validate_quantity(1.5) == Decimal("1.5")

    def test_zero_raises(self):
        with pytest.raises(InvalidQuantityError):
            validate_quantity(0)

    def test_negative_raises(self):
        with pytest.raises(InvalidQuantityError):
            validate_quantity(-1)

    def test_string_raises(self):
        with pytest.raises(InvalidQuantityError):
            validate_quantity("lots")


class TestValidatePrice:
    def test_valid(self):
        assert validate_price("44000") == Decimal("44000")

    def test_none_not_required(self):
        assert validate_price(None) is None

    def test_none_required_raises(self):
        with pytest.raises(MissingPriceError):
            validate_price(None, required=True)

    def test_zero_raises(self):
        with pytest.raises(InvalidPriceError):
            validate_price(0)

    def test_negative_raises(self):
        with pytest.raises(InvalidPriceError):
            validate_price(-100)


class TestValidateOrderParams:
    def test_market_order(self):
        result = validate_order_params("BTCUSDT", "BUY", "MARKET", "0.001")
        assert result["symbol"] == "BTCUSDT"
        assert result["side"] == "BUY"
        assert result["order_type"] == "MARKET"
        assert result["quantity"] == Decimal("0.001")
        assert result["price"] is None

    def test_limit_order_requires_price(self):
        with pytest.raises(MissingPriceError):
            validate_order_params("BTCUSDT", "BUY", "LIMIT", "0.001", price=None)

    def test_limit_order_with_price(self):
        result = validate_order_params("BTCUSDT", "SELL", "LIMIT", "0.001", price=44000)
        assert result["price"] == Decimal("44000")