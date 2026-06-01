"""
bot/exceptions.py
~~~~~~~~~~~~~~~~~
Custom exception hierarchy for the trading bot.

Having typed exceptions lets callers catch *exactly* what they care about
instead of catching broad `Exception` and guessing what went wrong.

Interviewer talking point:
  "I designed a small exception hierarchy so each layer of the app can raise
   domain-specific errors. The CLI layer catches them all, formats the message,
   and exits with the right code — zero business logic leaks into error strings."
"""


class TradingBotError(Exception):
    """Base exception for all trading-bot errors."""


# ── Validation errors ────────────────────────────────────────────────────────

class ValidationError(TradingBotError):
    """Raised when user-supplied input fails validation."""


class InvalidSymbolError(ValidationError):
    """Symbol is not in the accepted format (e.g. BTCUSDT)."""


class InvalidSideError(ValidationError):
    """Order side must be BUY or SELL."""


class InvalidOrderTypeError(ValidationError):
    """Order type must be MARKET or LIMIT (or STOP_LIMIT for bonus)."""


class InvalidQuantityError(ValidationError):
    """Quantity must be a positive number."""


class InvalidPriceError(ValidationError):
    """Price must be a positive number (required for LIMIT orders)."""


class MissingPriceError(ValidationError):
    """LIMIT order submitted without a price."""


# ── API / network errors ─────────────────────────────────────────────────────

class APIError(TradingBotError):
    """Raised when the Binance API returns a non-2xx response."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {message}")


class NetworkError(TradingBotError):
    """Raised on connection timeouts, DNS failures, or SSL errors."""


class AuthenticationError(TradingBotError):
    """Raised when API key/secret is missing or invalid."""


# ── TWAP-specific errors ─────────────────────────────────────────────────────

class TWAPError(TradingBotError):
    """Raised when a TWAP execution encounters an unrecoverable error."""