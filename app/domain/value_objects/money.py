"""
Money value object for financial amounts.

Provides type-safe monetary values with validation and operations.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Union


@dataclass(frozen=True)
class Money:
    """
    Money value object with amount validation.

    Attributes:
        amount: Decimal amount with 2 decimal places precision.

    Raises:
        ValueError: If amount is negative or invalid.
    """

    amount: Decimal

    def __init__(self, amount: Union[Decimal, float, int, str]) -> None:
        """
        Initialize money with validation.

        Args:
            amount: Monetary value to validate and store.

        Raises:
            ValueError: Amount is negative or cannot be converted to Decimal.
        """
        try:
            decimal_amount = Decimal(str(amount)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        except Exception as e:
            raise ValueError(f"Invalid amount format: {amount}") from e

        if decimal_amount < 0:
            raise ValueError(f"Amount cannot be negative: {amount}")

        # Use __setattr__ because of frozen=True
        object.__setattr__(self, "amount", decimal_amount)

    def __add__(self, other: "Money") -> "Money":
        """Add two money amounts."""
        return Money(self.amount + other.amount)

    def __mul__(self, factor: Union[int, float, Decimal]) -> "Money":
        """Multiply money by a factor."""
        return Money(self.amount * Decimal(str(factor)))

    def __str__(self) -> str:
        return f"{self.amount:,.2f}"

    def __repr__(self) -> str:
        return f"Money('{self.amount}')"
