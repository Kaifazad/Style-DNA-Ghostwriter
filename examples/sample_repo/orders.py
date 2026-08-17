"""Order processing utilities for the sample shop service."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class OrderValidationError(Exception):
    """Raised when an order fails validation."""


def _normalize_sku(sku: str) -> str:
    return sku.strip().upper()


def get_order_total(items: list[dict], tax_rate: float = 0.08) -> float:
    """Compute the total price for an order.

    Args:
        items: List of line items with 'price' and 'quantity'.
        tax_rate: Tax rate to apply.

    Returns:
        The total order price including tax.
    """
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    return round(subtotal * (1 + tax_rate), 2)


def validate_order(items: list[dict]) -> None:
    """Validate that an order's line items are well formed.

    Args:
        items: List of line items to validate.

    Raises:
        OrderValidationError: If any item is missing required fields.
    """
    for item in items:
        try:
            _ = item["sku"], item["price"], item["quantity"]
        except KeyError as exc:
            logger.error("Order item missing required field: %s", exc)
            raise OrderValidationError(f"Invalid item: {item}") from exc


def get_shipping_estimate(zip_code: str, weight_kg: float) -> Optional[float]:
    """Estimate shipping cost, or None if the zip code is unsupported."""
    if not zip_code.isdigit():
        return None
    base_rate = 4.99
    return round(base_rate + weight_kg * 0.75, 2)
