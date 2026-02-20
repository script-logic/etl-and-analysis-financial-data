"""
Client entity representing a customer.

Uses Pydantic for validation and serialization.
"""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Gender(StrEnum):
    """Client gender enumeration."""

    MALE = "Мужчина"
    FEMALE = "Женщина"
    OTHER = "Другой"
    UNKNOWN = "Не указан"


class NetWorthLevel(StrEnum):
    """Net worth level categorization."""

    LOW = "Низкий капитал"
    MEDIUM = "Средний капитал"
    HIGH = "Высокий капитал"

    @classmethod
    def from_amount(cls, amount: float) -> "NetWorthLevel":
        """
        Determine net worth level from amount.

        Args:
            amount: Net worth amount.

        Returns:
            Appropriate net worth level.
        """
        if amount < 100_000:
            return cls.LOW
        elif amount <= 1_000_000:
            return cls.MEDIUM
        else:
            return cls.HIGH


class Client(BaseModel):
    """
    Client domain entity.

    Attributes:
        id: Unique client identifier (UUID).
        age: Client age (0-150).
        gender: Client gender.
        net_worth: Client's net worth in currency units.
    """

    id: UUID | None = Field(default=None, description="Client UUID identifier")
    age: int | None = Field(
        default=None, ge=0, le=150, description="Client age (0-150)"
    )
    gender: Gender = Field(default=Gender.UNKNOWN, description="Client gender")
    net_worth: float | None = Field(
        default=None, ge=0, description="Client net worth"
    )

    @field_validator("net_worth", mode="before")
    @classmethod
    def validate_net_worth(cls, v: float | None) -> float | None:
        """Validate and clean net worth value."""
        if v is None:
            return None
        return round(float(v), 2)

    @property
    def net_worth_level(self) -> NetWorthLevel | None:
        """Get net worth level category."""
        if self.net_worth is None:
            return None
        return NetWorthLevel.from_amount(self.net_worth)

    @property
    def has_valid_id(self) -> bool:
        """Check if client has valid ID."""
        return self.id is not None

    class Config:
        """Pydantic configuration."""

        frozen = True
        use_enum_values = False
        json_encoders = {
            UUID: str,
            Gender: lambda v: v.value,
        }
