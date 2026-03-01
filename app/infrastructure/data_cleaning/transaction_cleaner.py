from datetime import datetime
from uuid import UUID

from structlog import get_logger

from app.domain.entities import FinanceServiceType, PaymentMethod, Transaction

from .interfaces import DataCleaner, NonFixableRule

logger = get_logger(__name__)


class TransactionCleaner(DataCleaner[Transaction]):
    """
    Cleans and validates transactions.

    Applies a series of validation rules and fixes where possible.
    """

    def __init__(self, rules: list[NonFixableRule[Transaction]] | None = None):
        """
        Initialize cleaner with rules.

        Args:
            rules: List of validation rules. If None, uses default rules.
        """
        self.rules = rules or self._get_default_rules()

    def _get_default_rules(self) -> list[NonFixableRule[Transaction]]:
        """Get default set of validation rules."""
        return [
            TransactionIdRule(),
            ClientIdRule(),
            TransactionDateRule(),
            AmountRule(),
            ServiceRule(),
            PaymentMethodRule(),
            CityRule(),
            ConsultantRule(),
        ]

    def clean(self, entity: Transaction) -> Transaction | None:
        """
        Clean and validate transaction.

        Args:
            entity: Raw transaction to clean.

        Returns:
            Cleaned transaction or None if it should be skipped.
        """
        if entity is None:
            return None

        for rule in self.rules:
            is_valid, error = rule.validate(entity)
            if not is_valid:
                logger.debug(
                    f"Transaction {entity.id} failed validation: {error}"
                )
                return None

        return entity


class TransactionIdRule(NonFixableRule[Transaction]):
    """Validate transaction ID."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.id is None:
            return False, "Missing transaction ID"

        try:
            if isinstance(entity.id, str):
                UUID(entity.id)
            return True, None
        except (ValueError, AttributeError):
            return False, f"Invalid transaction ID format: {entity.id}"


class ClientIdRule(NonFixableRule[Transaction]):
    """Validate client ID."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.client_id is None:
            return False, "Missing client ID"
        return True, None


class TransactionDateRule(NonFixableRule[Transaction]):
    """Validate transaction date."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.transaction_date is None:
            return False, "Missing transaction date"

        if entity.transaction_date > datetime.now():
            return False, f"Future date: {entity.transaction_date}"

        if entity.transaction_date.year < 2000:
            return False, f"Date too old: {entity.transaction_date}"

        return True, None


class AmountRule(NonFixableRule[Transaction]):
    """Validate transaction amount."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.amount <= 0:
            return False, f"Invalid amount: {entity.amount}"

        if entity.amount > 1_000_000_000_000:
            logger.warning(
                f"Unusually large amount: {entity.amount} for "
                f"transaction {entity.id}"
            )

        return True, None


class ServiceRule(NonFixableRule[Transaction]):
    """Validate service type."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.raw_service == "EMPTY":
            return False, "Missing service type"

        if entity.service_category == FinanceServiceType.UNKNOWN:
            logger.debug(f"Unknown service type: {entity.raw_service}")

        return True, None


class PaymentMethodRule(NonFixableRule[Transaction]):
    """Validate payment method."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.raw_payment_method == "EMPTY":
            return False, "Missing payment method"

        if entity.payment_method_category == PaymentMethod.UNKNOWN:
            logger.debug(
                f"Unknown payment method: {entity.raw_payment_method}"
            )

        return True, None


class CityRule(NonFixableRule[Transaction]):
    """Validate city name."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.city is None or entity.city == "EMPTY":
            return True, None

        if len(entity.city) > 100:
            return False, f"City name too long: {entity.city}"

        return True, None


class ConsultantRule(NonFixableRule[Transaction]):
    """Validate consultant name."""

    def validate(self, entity: Transaction) -> tuple[bool, str | None]:
        if entity.consultant is None or entity.consultant == "EMPTY":
            return True, None

        if len(entity.consultant) > 100:
            return False, f"Consultant name too long: {entity.consultant}"

        return True, None
