"""
Interfaces for data loading strategies.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Iterator, Generic, TypeVar

T = TypeVar("T")


class DataLoader(ABC, Generic[T]):
    """Base interface for all data loaders."""

    @abstractmethod
    def load(self, source: Path) -> Iterator[T]:
        """
        Load data from source and yield domain entities.

        Args:
            source: Path to data file.

        Yields:
            Domain entities one by one to manage memory.

        Raises:
            FileNotFoundError: If source doesn't exist.
            ValueError: If data format is invalid.
        """
        pass

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Check if this loader can handle the given source."""
        pass


class ExcelLoader(DataLoader[T], ABC):
    """Interface for Excel-specific loaders."""

    @abstractmethod
    def load_sheet(self, source: Path, sheet_name: str) -> Iterator[T]:
        """Load data from specific Excel sheet."""
        pass


class JsonLoader(DataLoader[T], ABC):
    """Interface for JSON-specific loaders."""

    @abstractmethod
    def load_stream(
        self, source: Path, chunk_size: int = 1000
    ) -> Iterator[List[T]]:
        """
        Load JSON data in chunks for large files.

        Args:
            source: Path to JSON file.
            chunk_size: Number of records per chunk.

        Yields:
            Lists of domain entities.
        """
        pass
