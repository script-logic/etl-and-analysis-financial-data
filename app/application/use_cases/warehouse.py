"""
ETL use case: Extract -> Clean -> Load data into warehouse.
"""

from pathlib import Path

from structlog import get_logger

from app.infrastructure.data_cleaning import ClientCleaner, TransactionCleaner
from app.infrastructure.data_loading import LoaderFactory
from app.infrastructure.database import (
    ClientRepository,
    TransactionRepository,
    Warehouse,
    create_warehouse,
)

logger = get_logger(__name__)


class BuildWarehouseUseCase:
    """
    ETL pipeline for building the data warehouse.

    1. Extract: Load raw data from Excel/JSON
    2. Clean: Apply validation rules
    3. Load: Save cleaned data to SQLite
    """

    def __init__(
        self,
        warehouse: Warehouse,
        loader_factory: LoaderFactory | None = None,
        transaction_cleaner: TransactionCleaner | None = None,
        client_cleaner: ClientCleaner | None = None,
    ):
        """
        Initialize ETL use case.

        Args:
            warehouse: Database warehouse instance.
            loader_factory: Factory for creating data loaders.
            transaction_cleaner: Cleaner for transactions.
            client_cleaner: Cleaner for clients.
        """
        self.warehouse = warehouse
        self.loader_factory = loader_factory or LoaderFactory()
        self.transaction_cleaner = transaction_cleaner or TransactionCleaner()
        self.client_cleaner = client_cleaner or ClientCleaner()

    def execute(
        self,
        transactions_path: Path,
        clients_path: Path,
        clear_existing: bool = False,
    ) -> dict[str, int]:
        """
        Run the ETL pipeline.

        Args:
            transactions_path: Path to transactions Excel file.
            clients_path: Path to clients JSON file.
            clear_existing: If True, clear database before loading.

        Returns:
            Dict with counts of loaded records.
        """
        logger.info("Starting ETL pipeline")

        if clear_existing:
            self.warehouse.clear_all()
            logger.info("Cleared existing data")

        session = self.warehouse.get_session()

        try:
            transactions_loaded = self._load_transactions(
                session, transactions_path
            )

            clients_loaded = self._load_clients(session, clients_path)

            session.commit()

            result = {
                "transactions_loaded": transactions_loaded,
                "clients_loaded": clients_loaded,
            }

            logger.info(f"ETL completed: {result}")
            return result

        except Exception as e:
            session.rollback()
            logger.error(f"ETL failed: {e}")
            raise
        finally:
            session.close()

    def _load_transactions(self, session, path: Path) -> int:
        """Load and clean transactions."""

        loader = self.loader_factory.get_transaction_loader(path)
        repo = TransactionRepository(session)

        count = 0
        skipped = 0

        for raw_transaction in loader.load(path):
            cleaned = self.transaction_cleaner.clean(raw_transaction)

            if cleaned:
                repo.add(cleaned)
                count += 1

                if count % 1000 == 0:
                    session.flush()
                    logger.debug(f"Processed {count} transactions")
            else:
                skipped += 1

        logger.info(f"Transactions: {count} loaded, {skipped} skipped")
        return count

    def _load_clients(self, session, path: Path) -> int:
        """Load and clean clients."""

        loader = self.loader_factory.get_client_loader(path)
        repo = ClientRepository(session)

        count = 0
        skipped = 0

        for raw_client in loader.load(path):
            cleaned = self.client_cleaner.clean(raw_client)

            if cleaned:
                repo.add(cleaned)
                count += 1

                if count % 1000 == 0:
                    session.flush()
                    logger.debug(f"Processed {count} clients")
            else:
                skipped += 1

        logger.info(f"Clients: {count} loaded, {skipped} skipped")
        return count


def build_warehouse(
    transactions_path: Path | str,
    clients_path: Path | str,
    db_path: Path | str = ":memory:",
    clear: bool = False,
) -> dict[str, int]:
    """
    Build the warehouse with default configuration.

    Args:
        transactions_path: Path to transactions Excel file.
        clients_path: Path to clients JSON file.
        db_path: Path to SQLite database.
        clear: If True, clear existing data.

    Returns:
        Dict with counts of loaded records.
    """
    transactions_path = Path(transactions_path)
    clients_path = Path(clients_path)

    warehouse = create_warehouse(db_path)
    use_case = BuildWarehouseUseCase(warehouse)

    try:
        return use_case.execute(transactions_path, clients_path, clear)
    finally:
        warehouse.close()
