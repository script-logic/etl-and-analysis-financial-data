import pandas as pd
from pathlib import Path
from typing import Iterator, Optional, Any
from uuid import UUID

from app.domain.entities.transaction import (
    Transaction,
    FinanceServiceType,
    PaymentMethod,
)
from app.infrastructure.data_loading.interfaces import ExcelLoader
import logging

logger = logging.getLogger(__name__)


class TransactionExcelLoader(ExcelLoader[Transaction]):
    """
    Loads transactions from Excel file.

    Expected columns:
        transaction_id, client_id, transaction_date, service,
        amount, payment_method, city, consultant
    """

    REQUIRED_COLUMNS = {
        "transaction_id",
        "client_id",
        "transaction_date",
        "service",
        "amount",
        "payment_method",
        "city",
        "consultant",
    }

    def __init__(self, sheet_name: str | int = 0):
        """
        Initialize Excel loader.

        Args:
            sheet_name: Excel sheet name or index to read.
        """
        self.sheet_name = sheet_name

    def supports(self, source: Path) -> bool:
        """Check if file is Excel."""
        return source.suffix.lower() in (".xlsx", ".xls")

    def load(self, source: Path) -> Iterator[Transaction]:
        """
        Load transactions from Excel file.

        Args:
            source: Path to Excel file.

        Yields:
            Transaction entities.

        Raises:
            FileNotFoundError: If file doesn't exist.
            ValueError: If required columns are missing.
        """
        if not source.exists():
            raise FileNotFoundError(f"Excel file not found: {source}")

        logger.info(f"Loading transactions from {source}")

        try:
            df = pd.read_excel(
                io=source,
                sheet_name=self.sheet_name,
                dtype=str,
                keep_default_na=False,
                na_values=["", "null", "NULL", "None"],
                engine="openpyxl" if source.suffix == ".xlsx" else None,
            )

            missing_cols = self.REQUIRED_COLUMNS - set(df.columns)
            if missing_cols:
                raise ValueError(f"Missing columns: {missing_cols}")

            logger.info(f"Loaded {len(df)} rows from Excel")

            for _, row in df.iterrows():
                transaction = self._row_to_transaction(row)
                if transaction:
                    yield transaction

        except Exception as e:
            logger.error(f"Failed to load Excel file: {e}")
            raise

    def load_sheet(
        self, source: Path, sheet_name: str | int
    ) -> Iterator[Transaction]:
        """Load from specific sheet."""
        old_sheet = self.sheet_name
        self.sheet_name = sheet_name
        try:
            yield from self.load(source)
        finally:
            self.sheet_name = old_sheet

    def _row_to_transaction(self, row: pd.Series) -> Optional[Transaction]:
        """
        Convert Excel row to Transaction entity.

        Handles:
        - UUID parsing with fallback
        - Date parsing
        - Amount with comma decimal separator
        - Empty strings as None
        """
        try:
            transaction_id = self._parse_uuid(row.get("transaction_id"))
            client_id = self._parse_uuid(row.get("client_id"))

            transaction_date = self._parse_date(row.get("transaction_date"))

            amount = self._parse_amount(row.get("amount"))
            if amount is None:
                logger.warning(
                    f"Skipping transaction {transaction_id}: invalid amount"
                )
                return None

            raw_service = self._clean_string(row.get("service"))
            raw_payment_method = self._clean_string(row.get("payment_method"))
            city = self._clean_string(row.get("city"))
            consultant = self._clean_string(row.get("consultant"))

            return Transaction(
                id=transaction_id,
                client_id=client_id,
                transaction_date=transaction_date,
                raw_service=raw_service,
                amount=amount,
                raw_payment_method=raw_payment_method,
                city=city,
                consultant=consultant,
            )

        except Exception as e:
            logger.warning(f"Failed to parse row: {e}")
            return None

    def _parse_uuid(self, value: Any) -> Optional[UUID]:
        """Parse UUID from various formats."""
        if pd.isna(value) or not value:
            return None

        try:
            return UUID(str(value).strip())
        except (ValueError, AttributeError):
            logger.debug(f"Invalid UUID: {value}")
            return None

    def _parse_date(self, value: Any) -> Optional[pd.Timestamp]:
        """Parse date with fallback."""
        if pd.isna(value) or value in ("INVALID_DATE", ""):
            return None

        try:
            if isinstance(value, pd.Timestamp):
                return value

            date = pd.to_datetime(value, errors="coerce")
            return date if pd.notna(date) else None

        except Exception:
            return None

    def _parse_amount(self, value: Any) -> Optional[float]:
        """Parse amount with comma decimal separator."""
        if pd.isna(value):
            return None

        try:
            str_value = str(value).strip().replace(" ", "")

            if "," in str_value and "." not in str_value:
                str_value = str_value.replace(",", ".")

            amount = float(str_value)
            return amount if amount > 0 else None

        except (ValueError, TypeError):
            return None

    def _clean_string(self, value: Any) -> str:
        """Clean string value."""
        if pd.isna(value) or value is None:
            return "EMPTY"

        cleaned = str(value).strip()
        return cleaned if cleaned else "EMPTY"

    def _to_service_enum(self, value: str) -> FinanceServiceType:
        """Convert string to FinanceServiceType enum."""
        try:
            return FinanceServiceType(value)
        except ValueError:
            logger.debug(f"Unknown service type: {value}, using UNKNOWN")
            return FinanceServiceType.UNKNOWN

    def _to_payment_enum(self, value: str) -> PaymentMethod:
        """Convert string to PaymentMethod enum."""
        try:
            return PaymentMethod(value)
        except ValueError:
            logger.debug(f"Unknown payment method: {value}, using UNKNOWN")
            return PaymentMethod.UNKNOWN
