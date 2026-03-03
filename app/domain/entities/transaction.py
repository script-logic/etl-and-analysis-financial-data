from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)
from pydantic.functional_validators import BeforeValidator

from app.domain.value_objects import Money


class FinanceServiceType(StrEnum):
    CAPITAL_STRUCTURING = "Структурирование капитала"
    INVESTMENT_ADVISORY = "Инвестиционное консультирование"
    FINANCIAL_PLANNING = "Финансовое планирование"
    ASSET_MANAGEMENT = "Управление активами"
    TAX_PLANNING = "Налоговое планирование"
    UNKNOWN = "Неизвестная услуга"

    @classmethod
    def _missing_(cls, value: object) -> "FinanceServiceType":
        return cls.UNKNOWN


class PaymentMethod(StrEnum):
    BANK_TRANSFER = "Банковский перевод"
    CREDIT_CARD = "Кредитная карта"
    CASH = "Наличные"
    CRYPTOCURRENCY = "Криптовалюта"
    UNKNOWN = "Неизвестно"

    @classmethod
    def _missing_(cls, value: object) -> "PaymentMethod":
        return cls.UNKNOWN


def validate_amount(v: Any) -> float:
    """Validate and clean amount value."""
    try:
        if isinstance(v, str):
            v = v.replace(",", ".")
        amount = float(v)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid amount format: {v}") from e
    if amount <= 0:
        raise ValueError(f"Amount must be positive: {amount}")
    return round(amount, 2)


def validate_date(v: Any) -> datetime | None:
    """Validate and parse date."""
    if v is None or v == "INVALID_DATE":
        return None
    if isinstance(v, datetime):
        return v
    if not isinstance(v, str):
        return None

    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%Y-%m-%d",
    ]:
        try:
            return datetime.strptime(v, fmt)
        except ValueError:
            continue
    return None


def clean_string(v: Any) -> str | None:
    """Clean string fields."""
    if v is None or v == "":
        return None
    if not isinstance(v, str):
        v = str(v)
    cleaned = " ".join(v.split())
    if cleaned.lower() in ["неизвестный консультант", "неизвестно"]:
        return None
    return cleaned if cleaned else None


AmountField = Annotated[float, BeforeValidator(validate_amount)]
DateField = Annotated[datetime | None, BeforeValidator(validate_date)]
StringField = Annotated[str | None, BeforeValidator(clean_string)]


class Transaction(BaseModel):
    id: UUID | None = Field(default=None)
    client_id: UUID | None = Field(default=None)
    transaction_date: DateField = Field(default=None)
    raw_service: str = Field("EMPTY")
    amount: AmountField = Field(..., gt=0)
    raw_payment_method: str = Field("EMPTY")
    city: StringField = Field(default=None)
    consultant: StringField = Field(default=None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def service_category(self) -> FinanceServiceType:
        try:
            return FinanceServiceType(self.raw_service)
        except ValueError:
            return FinanceServiceType.UNKNOWN

    @computed_field  # type: ignore[prop-decorator]
    @property
    def payment_method_category(self) -> PaymentMethod:
        try:
            return PaymentMethod(self.raw_payment_method)
        except ValueError:
            return PaymentMethod.UNKNOWN

    @property
    def money_amount(self) -> Money:
        return Money(self.amount)

    model_config = ConfigDict(
        frozen=True,
        json_encoders={
            UUID: str,
            datetime: lambda v: v.isoformat(),
        },
    )
