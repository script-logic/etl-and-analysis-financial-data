"""
Domain layer containing business entities and value objects.

This layer is framework-agnostic and contains core business logic.
"""

from .entities.client import Client, Gender, NetWorthLevel
from .entities.transaction import (
    Transaction,
    FinanceServiceType,
    PaymentMethod,
)
from .value_objects.money import Money

__all__ = [
    # Entities
    "Client",
    "Transaction",
    # Enums
    "Gender",
    "NetWorthLevel",
    "FinanceServiceType",
    "PaymentMethod",
    # Value Objects
    "Money",
]
