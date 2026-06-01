"""
bot/client.py
~~~~~~~~~~~~~
Low-level Binance Futures Testnet HTTP client.

Responsibilities:
  • Sign every request with HMAC-SHA256 (Binance requirement)
  • Send HTTP requests via httpx
  • Map HTTP / Binance error codes to typed exceptions
  • Log every request and response at DEBUG level

Interviewer talking point:
  "I isolated the HTTP/auth layer entirely. If Binance changes its auth
   scheme, or if we switch to WebSockets, only this file changes — nothing
   in the orders or CLI layer needs to know."
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from bot.exceptions import APIError, AuthenticationError, NetworkError
from bot.logging_config import get_logger

logger = get_logger(__name__)

BASE_URL = "https://testnet.binancefuture.com"

EP_ORDER         = "/fapi/v1/order"
EP_PING          = "/fapi/v1/ping"
EP_SERVER_TIME   = "/fapi/v1/time"
EP_EXCHANGE_INFO = "/fapi/v1/exchangeInfo"
EP_ACCOUNT       = "/fapi/v2/account"


class BinanceClient:
    """Thin, stateless wrapper around the Binance Futures REST API."""

    def __init__(self, api_key: str, api_secret: str, timeout: float = 10.0) -> None:
        if not api_key or not api_secret:
            raise AuthenticationError(
                "API_KEY and API_SECRET must be set. "
                "Copy .env.example to .env and fill in your testnet credentials."
            )
        self._api_key = api_key
        self._api_secret = api_secret.encode()

        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={
                "X-MBX-APIKEY": api_key,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=timeout,
        )
        logger.debug("BinanceClient initialised", extra={"base_url": BASE_URL})

    # ── Private helpers ───────────────────────────────────────────────────────

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add HMAC-SHA256 signature to params dict."""
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret,
            query_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _get(self, endpoint: str, params: dict | None = None, *, signed: bool = False) -> dict:
        """Execute a GET request."""
        p = dict(params or {})
        if signed:
            p = self._sign(p)

        logger.debug(
            "GET request",
            extra={"endpoint": endpoint, "params": {k: v for k, v in p.items() if k != "signature"}},
        )

        try:
            resp = self._http.get(endpoint, params=p)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request to {endpoint} timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error on {endpoint}: {exc}") from exc

        return self._handle_response(resp)

    def _post(self, endpoint: str, params: dict | None = None, *, signed: bool = True) -> dict:
        """Execute a signed POST request."""
        p = dict(params or {})
        if signed:
            p = self._sign(p)

        safe_params = {k: v for k, v in p.items() if k != "signature"}
        logger.debug(
            "POST request",
            extra={"endpoint": endpoint, "params": safe_params},
        )

        try:
            resp = self._http.post(endpoint, data=p)
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request to {endpoint} timed out: {exc}") from exc
        except httpx.RequestError as exc:
            raise NetworkError(f"Network error on {endpoint}: {exc}") from exc

        return self._handle_response(resp)

    @staticmethod
    def _handle_response(resp: httpx.Response) -> dict:
        """Parse response, raise APIError on failures."""
        logger.debug(
            "API response",
            extra={"status_code": resp.status_code, "url": str(resp.url)},
        )

        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            return {}

        if resp.status_code != 200:
            code = data.get("code", resp.status_code)
            message = data.get("msg", resp.text)
            logger.error(
                "API error response",
                extra={"http_status": resp.status_code, "binance_code": code, "msg": message},
            )
            raise APIError(resp.status_code, code, message)

        logger.debug("API success response", extra={"response_keys": list(data.keys()) if isinstance(data, dict) else "list"})
        return data

    # ── Public API methods ────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the testnet is reachable."""
        try:
            self._get(EP_PING)
            logger.info("Testnet ping successful")
            return True
        except Exception as exc:
            logger.warning("Testnet ping failed", extra={"error": str(exc)})
            return False

    def get_server_time(self) -> int:
        """Return Binance server time in epoch milliseconds."""
        data = self._get(EP_SERVER_TIME)
        return data["serverTime"]

    def get_exchange_info(self) -> dict:
        """Return full exchange info."""
        return self._get(EP_EXCHANGE_INFO)

    def get_account(self) -> dict:
        """Return account info including balance and positions."""
        return self._get(EP_ACCOUNT, signed=True)

    def place_order(self, params: dict[str, Any]) -> dict:
        """Place an order and return the raw API response dict."""
        logger.info(
            "Placing order",
            extra={
                "symbol":   params.get("symbol"),
                "side":     params.get("side"),
                "type":     params.get("type"),
                "quantity": params.get("quantity"),
            },
        )
        result = self._post(EP_ORDER, params)
        logger.info(
            "Order placed",
            extra={
                "orderId":      result.get("orderId"),
                "status":       result.get("status"),
                "executedQty":  result.get("executedQty"),
                "avgPrice":     result.get("avgPrice"),
            },
        )
        return result

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "BinanceClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()