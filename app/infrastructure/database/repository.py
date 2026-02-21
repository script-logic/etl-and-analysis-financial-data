"""
Repository pattern for database access.

Separates business logic from data access logic.
"""

import json
from datetime import datetime, timedelta
from sqlite3 import IntegrityError
from typing import List, Dict, Any, Optional, TypedDict
from sqlalchemy import case, func, desc, and_
from sqlalchemy.orm import Session
from structlog import get_logger

from .models import (
    ClientTable,
    TransactionTable,
    AnalysisResultTable,
)
from app.domain.entities.transaction import Transaction
from app.domain.entities.client import Client


LevelValues = TypedDict(
    "LevelValues", {"name": str, "revenue": float, "count": int}
)

logger = get_logger(__name__)


class ClientSegmentAnalysis(TypedDict):
    """Analysis result by client segment."""

    segment: str
    total_revenue: float
    transaction_count: int
    avg_transaction: float
    client_count: int


class TransactionRepository:
    """Repository for transaction operations."""

    def __init__(self, session: Session):
        self.session = session
        self._seen_in_session: set[str] = set()

    def add(self, transaction: Transaction) -> None:
        """
        Add a single transaction to database using merge to handle duplicates.

        Args:
            transaction: Domain transaction entity
        """
        if not transaction.id:
            logger.debug("Skipping transaction without ID")
            return

        transaction_id = str(transaction.id)
        if transaction_id in self._seen_in_session:
            return

        orm_obj = TransactionTable(
            id=transaction_id,
            client_id=(
                str(transaction.client_id) if transaction.client_id else None
            ),
            raw_service=transaction.raw_service,
            raw_payment_method=transaction.raw_payment_method,
            transaction_date=transaction.transaction_date,
            amount=transaction.amount,
            city=transaction.city,
            consultant=transaction.consultant,
            service_category=transaction.service_category.value,
            payment_method_category=(
                transaction.payment_method_category.value or "UNKNOWN"
            ),
        )

        self.session.merge(orm_obj)
        self._seen_in_session.add(transaction_id)

    def add_many(self, transactions: List[Transaction]) -> None:
        """Bulk insert multiple transactions with duplicate detection."""
        self._seen_in_session.clear()

        for transaction in transactions:
            self.add(transaction)

        try:
            self.session.flush()
        except IntegrityError as e:
            logger.error(f"Integrity error during bulk insert: {e}")
            self.session.rollback()
            raise

    def clear_batch_cache(self) -> None:
        """Clear the batch duplicate cache."""
        self._seen_in_session.clear()

    def get_top_services_by_count(
        self, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top N services by number of orders.

        Args:
            limit: Number of top services to return

        Returns:
            List of dicts with service name and order count
        """
        result = (
            self.session.query(
                TransactionTable.raw_service.label("service"),
                func.count().label("order_count"),
            )
            .group_by(TransactionTable.raw_service)
            .order_by(desc("order_count"))
            .limit(limit)
            .all()
        )

        return [{"service": r.service, "count": r.order_count} for r in result]

    def get_service_with_max_revenue(self) -> Optional[Dict[str, Any]]:
        """
        Find service with highest total revenue.

        Returns:
            Dict with service name and total revenue, or None if no data
        """
        result = (
            self.session.query(
                TransactionTable.raw_service.label("service"),
                func.sum(TransactionTable.amount).label("total_revenue"),
            )
            .group_by(TransactionTable.raw_service)
            .order_by(desc("total_revenue"))
            .first()
        )

        if result:
            return {"service": result.service, "revenue": result.total_revenue}
        return None

    def get_avg_amount_by_city(self) -> List[Dict[str, Any]]:
        """
        Calculate average transaction amount per city.

        Returns:
            List of dicts with city and average amount
        """
        result = (
            self.session.query(
                TransactionTable.city,
                func.avg(TransactionTable.amount).label("avg_amount"),
                func.count().label("transaction_count"),
            )
            .filter(TransactionTable.city.isnot(None))
            .group_by(TransactionTable.city)
            .order_by(desc("avg_amount"))
            .all()
        )

        return [
            {
                "city": r.city,
                "avg_amount": round(r.avg_amount, 2),
                "count": r.transaction_count,
            }
            for r in result
        ]

    def get_payment_method_distribution(self) -> Dict[str, float]:
        """
        Calculate percentage distribution of payment methods.

        Returns:
            Dict with payment method as key and percentage as value
        """
        total = self.session.query(func.count(TransactionTable.id)).scalar()
        if not total:
            return {}

        result = (
            self.session.query(
                TransactionTable.raw_payment_method.label("method"),
                (func.count() * 100.0 / total).label("percentage"),
            )
            .group_by(TransactionTable.raw_payment_method)
            .order_by(desc("percentage"))
            .all()
        )

        return {r.method: round(r.percentage, 2) for r in result}

    def get_last_month_revenue(self) -> float:
        """
        Calculate total revenue for the last month in the data.
        """
        max_date = self.session.query(
            func.max(TransactionTable.transaction_date)
        ).scalar()

        if not max_date:
            return 0.0

        if max_date.month == 1:
            last_month_start = datetime(max_date.year - 1, 12, 1)
        else:
            last_month_start = datetime(max_date.year, max_date.month - 1, 1)

        last_month_end = datetime(
            max_date.year, max_date.month, 1
        ) - timedelta(days=1)

        result = (
            self.session.query(func.sum(TransactionTable.amount))
            .filter(
                and_(
                    TransactionTable.transaction_date >= last_month_start,
                    TransactionTable.transaction_date <= last_month_end,
                )
            )
            .scalar()
        )

        return result or 0.0

    def get_monthly_revenue_trend(
        self, months: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Get monthly revenue trend for the last N months of data.
        """
        max_date = self.session.query(
            func.max(TransactionTable.transaction_date)
        ).scalar()

        if not max_date:
            return []

        if max_date.month > months:
            since_date = datetime(max_date.year, max_date.month - months, 1)
        else:
            since_date = datetime(
                max_date.year - 1, 12 - (months - max_date.month), 1
            )

        year = func.strftime("%Y", TransactionTable.transaction_date)
        month = func.strftime("%m", TransactionTable.transaction_date)

        result = (
            self.session.query(
                year.label("year"),
                month.label("month"),
                func.sum(TransactionTable.amount).label("revenue"),
                func.count().label("transaction_count"),
            )
            .filter(TransactionTable.transaction_date >= since_date)
            .group_by(year, month)
            .order_by(year, month)
            .all()
        )

        monthly_data = []
        for r in result:
            monthly_data.append(
                {
                    "year": r.year,
                    "month": r.month,
                    "period": f"{r.year}-{r.month}",
                    "revenue": float(r.revenue) if r.revenue else 0.0,
                    "transaction_count": r.transaction_count or 0,
                }
            )

        return monthly_data

    def get_service_performance(self) -> List[Dict[str, Any]]:
        """
        Comprehensive service performance analysis.

        Returns:
            List of services with revenue, count, avg, min, max.
        """
        result = (
            self.session.query(
                TransactionTable.raw_service.label("service"),
                func.count().label("order_count"),
                func.sum(TransactionTable.amount).label("total_revenue"),
                func.avg(TransactionTable.amount).label("avg_amount"),
                func.min(TransactionTable.amount).label("min_amount"),
                func.max(TransactionTable.amount).label("max_amount"),
            )
            .group_by(TransactionTable.raw_service)
            .order_by(desc("total_revenue"))
            .all()
        )

        return [
            {
                "service": r.service,
                "order_count": r.order_count,
                "total_revenue": r.total_revenue,
                "avg_amount": round(r.avg_amount, 2),
                "min_amount": r.min_amount,
                "max_amount": r.max_amount,
                "revenue_percentage": 0,
            }
            for r in result
        ]

    def enrich_with_percentages(self, services: List[Dict]) -> List[Dict]:
        """Add percentage columns to service analysis."""
        if not services:
            return services

        total_revenue = sum(s["total_revenue"] for s in services)
        total_orders = sum(s["order_count"] for s in services)

        for service in services:
            service["revenue_percentage"] = (
                round((service["total_revenue"] / total_revenue * 100), 2)
                if total_revenue
                else 0
            )
            service["order_percentage"] = (
                round((service["order_count"] / total_orders * 100), 2)
                if total_orders
                else 0
            )

        return services


class ClientRepository:
    """Repository for client operations."""

    def __init__(self, session: Session):
        self.session = session

    def add(self, client: Client) -> None:
        """
        Add a single client to database.

        Args:
            client: Domain client entity
        """
        if not client.id:
            return

        orm_obj = ClientTable(
            id=str(client.id),
            age=client.age,
            gender=client.gender.value if client.gender else None,
            net_worth=client.net_worth,
        )
        self.session.merge(orm_obj)  # Use merge to handle duplicates

    def add_many(self, clients: List[Client]) -> None:
        """Bulk insert multiple clients."""
        for client in clients:
            self.add(client)

    def get_revenue_by_net_worth_level(self) -> List[LevelValues]:
        """
        Analyze revenue by client net worth level.

        Returns:
            List with revenue per net worth level
        """
        result = (
            self.session.query(
                ClientTable.net_worth,
                func.sum(TransactionTable.amount).label("total_revenue"),
                func.count(TransactionTable.id).label("transaction_count"),
            )
            .join(
                TransactionTable, ClientTable.id == TransactionTable.client_id
            )
            .group_by(ClientTable.id)
            .all()
        )

        levels: dict[str, LevelValues] = {
            "LOW": {"name": "Низкий капитал", "revenue": 0, "count": 0},
            "MEDIUM": {"name": "Средний капитал", "revenue": 0, "count": 0},
            "HIGH": {"name": "Высокий капитал", "revenue": 0, "count": 0},
        }

        for row in result:
            if row.net_worth is None:
                continue

            if row.net_worth < 100_000:
                level = "LOW"
            elif row.net_worth <= 1_000_000:
                level = "MEDIUM"
            else:
                level = "HIGH"

            levels[level]["revenue"] += row.total_revenue or 0
            levels[level]["count"] += row.transaction_count

        return list(levels.values())

    def get_detailed_revenue_by_segment(self) -> List[ClientSegmentAnalysis]:
        """
        Detailed analysis of revenue by client net worth segments.

        Returns:
            List with revenue, counts and averages per segment.
        """
        segment_case = case(
            (ClientTable.net_worth < 100_000, "Низкий капитал"),
            (
                ClientTable.net_worth.between(100_000, 1_000_000),
                "Средний капитал",
            ),
            (ClientTable.net_worth > 1_000_000, "Высокий капитал"),
            else_="Неизвестно",
        ).label("segment")

        result = (
            self.session.query(
                segment_case,
                func.count(ClientTable.id.distinct()).label("client_count"),
                func.sum(TransactionTable.amount).label("total_revenue"),
                func.count(TransactionTable.id).label("transaction_count"),
                func.avg(TransactionTable.amount).label("avg_transaction"),
            )
            .join(
                TransactionTable,
                ClientTable.id == TransactionTable.client_id,
                isouter=True,  # LEFT JOIN to see clients without transactions
            )
            .group_by("segment")
            .order_by(desc("total_revenue"))
            .all()
        )

        return [
            {
                "segment": r.segment,
                "client_count": r.client_count,
                "total_revenue": r.total_revenue or 0,
                "transaction_count": r.transaction_count or 0,
                "avg_transaction": round(r.avg_transaction or 0, 2),
            }
            for r in result
        ]

    def get_clients_without_transactions(self) -> int:
        """Count clients who never made a transaction."""
        return (
            self.session.query(ClientTable)
            .outerjoin(
                TransactionTable, ClientTable.id == TransactionTable.client_id
            )
            .filter(TransactionTable.id.is_(None))
            .count()
        )


class AnalysisRepository:
    """Repository for storing/retrieving analysis results."""

    def __init__(self, session: Session):
        self.session = session

    def save_result(
        self, name: str, result: Any, parameters: Optional[Dict] = None
    ) -> None:
        """Save analysis result to database."""
        orm_obj = AnalysisResultTable(
            analysis_name=name,
            result_json=json.dumps(result, ensure_ascii=False, default=str),
            parameters=json.dumps(parameters) if parameters else None,
        )
        self.session.add(orm_obj)

    def get_latest_result(self, name: str) -> Optional[Dict]:
        """Get most recent analysis result."""
        result = (
            self.session.query(AnalysisResultTable)
            .filter(AnalysisResultTable.analysis_name == name)
            .order_by(desc(AnalysisResultTable.created_at))
            .first()
        )

        if result:
            return json.loads(result.result_json)
        return None
