from abc import ABC, abstractmethod
from typing import Generic, List, TypeVar

T = TypeVar("T")


class BaseValidationRule(ABC, Generic[T]):
    """Base class for all validation rules."""

    @abstractmethod
    def validate(self, entity: T) -> tuple[bool, str | None]:
        """
        Validate entity against rule.

        Returns:
            Tuple of (is_valid, error_message).
        """
        pass


class FixableRule(BaseValidationRule[T], ABC):
    """Rule that can automatically fix issues."""

    @abstractmethod
    def fix(self, entity: T) -> T:
        """
        Attempt to fix entity.

        Raises:
            ValueError: If fix is not possible.
        """
        pass


class NonFixableRule(BaseValidationRule[T], ABC):
    """Rule that cannot fix issues - validation only."""

    def can_fix(self) -> bool:
        return False


class DataCleaner(ABC, Generic[T]):
    """
    Base interface for all data cleaners.

    Cleans and validates domain entities before persistence.
    """

    @abstractmethod
    def clean(self, entity: T) -> T | None:
        """
        Clean and validate a single entity.

        Args:
            entity: Raw domain entity to clean.

        Returns:
            Cleaned entity or None if entity should be skipped.
        """
        pass

    def clean_batch(self, entities: List[T]) -> List[T]:
        """
        Clean a batch of entities.

        Default implementation calls clean() for each entity.

        Args:
            entities: List of raw entities.

        Returns:
            List of cleaned entities (skipped ones are filtered out).
        """
        return [
            e
            for e in (self.clean(entity) for entity in entities)
            if e is not None
        ]
