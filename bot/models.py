"""
bot/models.py
~~~~~~~~~~~~~
Typed dataclass models for Binance API responses.

Using dataclasses instead of raw dicts gives us:
  • IDE auto-complete on every field
  • Type safety — a typo in a field name is caught at import time
  • Easy serialisation to dict / JSON for logging

Interviewer talking point:
  "I use dataclasses as lightweight value objects. They document the shape
   of the API response right in the code, making it immediately obvious what
   fields we depend on — no more hunting through API docs mid-review."
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class OrderResponse:
    """Normalised representation of a Binance order response."""

    order_id: int
    symbol: str
    side: str
    order_type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str
    time_in_force: str
    client_order_id: str
    update_time: int
    cum_quote: str
    reduce_only: bool = False
    close_position: bool = False
    raw: dict = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @property
    def is_filled(self) -> bool:
        return self.status == "FILLED"

    @property
    def display_price(self) -> str:
        if self.avg_price and float(self.avg_price) > 0:
            return self.avg_price
        if self.price and float(self.price) > 0:
            return self.price
        return "market"

    @classmethod
    def from_api(cls, data: dict) -> "OrderResponse":
        return cls(
            order_id=data.get("orderId", 0),
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_type=data.get("type", ""),
            status=data.get("status", ""),
            orig_qty=data.get("origQty", "0"),
            executed_qty=data.get("executedQty", "0"),
            avg_price=data.get("avgPrice", "0"),
            price=data.get("price", "0"),
            time_in_force=data.get("timeInForce", "GTC"),
            client_order_id=data.get("clientOrderId", ""),
            update_time=data.get("updateTime", 0),
            cum_quote=data.get("cumQuote", "0"),
            reduce_only=data.get("reduceOnly", False),
            close_position=data.get("closePosition", False),
            raw=data,
        )


@dataclass
class TWAPResult:
    """Summary of a completed TWAP execution."""

    symbol: str
    side: str
    total_qty: float
    slices: int
    completed_slices: int
    failed_slices: int
    orders: list[OrderResponse] = field(default_factory=list)
    total_executed_qty: float = 0.0
    avg_fill_price: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.slices == 0:
            return 0.0
        return self.completed_slices / self.slices * 100