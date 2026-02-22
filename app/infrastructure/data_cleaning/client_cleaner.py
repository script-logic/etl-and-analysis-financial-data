from typing import List, Optional
from uuid import UUID

from structlog import get_logger

from app.domain.entities import Client

from .interfaces import DataCleaner, NonFixableRule

logger = get_logger(__name__)


class ClientCleaner(DataCleaner[Client]):
    """
    Cleans and validates clients.

    Applies validation rules and filters out invalid clients.
    """

    def __init__(self, rules: Optional[List[NonFixableRule[Client]]] = None):
        """Initialize cleaner with rules."""
        self.rules = rules or self._get_default_rules()

    def _get_default_rules(self) -> List[NonFixableRule[Client]]:
        """Get default validation rules."""
        return [
            ClientIdRule(),
            ClientAgeRule(),
            ClientGenderRule(),
            ClientNetWorthRule(),
        ]

    def clean(self, entity: Client) -> Client | None:
        """
        Clean and validate client.

        Args:
            entity: Raw client to clean.

        Returns:
            Cleaned client or None if should be skipped.
        """
        if entity is None:
            return None

        for rule in self.rules:
            is_valid, error = rule.validate(entity)
            if not is_valid:
                logger.debug(f"Client {entity.id} failed validation: {error}")
                return None

        return entity


class ClientIdRule(NonFixableRule[Client]):
    """Validate client ID."""

    def validate(self, entity: Client) -> tuple[bool, str | None]:
        if entity.id is None:
            return False, "Missing client ID"

        try:
            if isinstance(entity.id, str):
                UUID(entity.id)
            return True, None
        except (ValueError, AttributeError):
            return False, f"Invalid client ID format: {entity.id}"


class ClientAgeRule(NonFixableRule[Client]):
    """Validate client age."""

    def validate(self, entity: Client) -> tuple[bool, str | None]:
        if entity.age is None:
            return True, None

        if entity.age < 0 or entity.age > 150:
            return False, f"Invalid age: {entity.age}"

        return True, None


class ClientGenderRule(NonFixableRule[Client]):
    """Validate client gender."""

    def validate(self, entity: Client) -> tuple[bool, str | None]:
        return True, None


class ClientNetWorthRule(NonFixableRule[Client]):
    """Validate client net worth."""

    def validate(self, entity: Client) -> tuple[bool, str | None]:
        if entity.net_worth is None:
            return True, None

        if entity.net_worth < 0:
            return False, f"Negative net worth: {entity.net_worth}"

        return True, None
