from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, computed_field

from app.domain.value_objects.money import Money


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


class Transaction(BaseModel):
    id: UUID | None = Field(default=None)
    client_id: UUID | None = Field(default=None)
    transaction_date: datetime | None = Field(default=None)
    raw_service: str = Field("EMPTY")
    amount: float = Field(..., gt=0)
    raw_payment_method: str = Field("EMPTY")
    city: str | None = Field(default=None)
    consultant: str | None = Field(default=None)

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

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: float | str) -> float:
        try:
            if isinstance(v, str):
                v = v.replace(",", ".")
            amount = float(v)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid amount format: {v}") from e
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")
        return round(amount, 2)

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_date(cls, v: str | datetime | None) -> datetime | None:
        if v is None or v == "INVALID_DATE":
            return None
        if isinstance(v, datetime):
            return v
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

    @field_validator("city", "consultant", mode="before")
    @classmethod
    def clean_string(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        cleaned = " ".join(str(v).split())
        if cleaned.lower() in ["неизвестный консультант", "неизвестно"]:
            return None
        return cleaned if cleaned else None

    @property
    def money_amount(self) -> Money:
        return Money(self.amount)

    class Config:
        frozen = True
        json_encoders = {
            UUID: str,
            datetime: lambda v: v.isoformat(),
        }
