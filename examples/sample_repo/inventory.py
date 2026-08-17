"""Inventory tracking utilities for the sample shop service."""

import logging

logger = logging.getLogger(__name__)


class InventoryError(Exception):
    """Raised when an inventory operation cannot be completed."""


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def get_stock_level(sku: str, warehouse: dict) -> int:
    """Return the current stock level for a SKU.

    Args:
        sku: The item SKU to look up.
        warehouse: Mapping of SKU to stock count.

    Returns:
        The stock count, or 0 if the SKU is unknown.
    """
    return warehouse.get(sku, 0)


def reserve_stock(sku: str, quantity: int, warehouse: dict) -> None:
    """Reserve stock for an order.

    Args:
        sku: The item SKU to reserve.
        quantity: Amount to reserve.
        warehouse: Mapping of SKU to stock count (mutated in place).

    Raises:
        InventoryError: If there isn't enough stock available.
    """
    try:
        available = warehouse[sku]
    except KeyError as exc:
        logger.error("Unknown SKU during reservation: %s", exc)
        raise InventoryError(f"Unknown SKU: {sku}") from exc

    if available < quantity:
        logger.warning("Insufficient stock for %s: wanted %d, have %d", sku, quantity, available)
        raise InventoryError(f"Not enough stock for {sku}")

    warehouse[sku] = available - quantity


def get_reorder_recommendation(sku: str, warehouse: dict, threshold: int = 10) -> bool:
    """Return True if a SKU is at or below its reorder threshold."""
    return get_stock_level(sku, warehouse) <= threshold
