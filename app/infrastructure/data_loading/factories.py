"""
Factory for creating data loaders.
"""

from pathlib import Path

from structlog import get_logger

from app.domain.entities import Client, Transaction

from .excel_loader import TransactionExcelLoader
from .interfaces import DataLoader
from .json_loader import ClientJsonLoader

logger = get_logger(__name__)


class LoaderFactory:
    """
    Factory for creating appropriate loaders based on file extension.
    """

    def __init__(self) -> None:
        self._loaders: dict[str, type[DataLoader]] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register built-in loaders."""
        self.register(".xlsx", TransactionExcelLoader)
        self.register(".json", ClientJsonLoader)

    def register(self, extension: str, loader_class: type[DataLoader]) -> None:
        """Register a loader for a file extension."""
        if extension in self._loaders:
            logger.warning(f"Overwriting loader for {extension}")
        self._loaders[extension] = loader_class

    def get_loader(self, source: Path) -> DataLoader:
        """
        Get appropriate loader for the source file.

        Args:
            source: Path to data file.

        Returns:
            DataLoader instance.

        Raises:
            ValueError: If no loader supports the file.
        """
        extension = source.suffix.lower()

        if extension not in self._loaders:
            for loader_class in self._loaders.values():
                loader = loader_class()
                if loader.supports(source):
                    return loader

            raise ValueError(f"No loader found for {source}")

        loader_class = self._loaders[extension]
        return loader_class()

    def get_transaction_loader(self, source: Path) -> DataLoader[Transaction]:
        """Get loader for transactions."""
        loader = self.get_loader(source)
        if not isinstance(loader, TransactionExcelLoader):
            raise ValueError(
                f"Expected TransactionExcelLoader, got {type(loader)}"
            )
        return loader

    def get_client_loader(self, source: Path) -> DataLoader[Client]:
        """Get loader for clients."""
        loader = self.get_loader(source)
        if not isinstance(loader, ClientJsonLoader):
            raise ValueError(f"Expected ClientJsonLoader, got {type(loader)}")
        return loader
