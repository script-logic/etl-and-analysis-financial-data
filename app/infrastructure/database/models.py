"""
SQLAlchemy ORM models for the warehouse database.

These models represent the cleaned and normalized data structure.
"""

import inflection
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    declared_attr,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate table name from class name (lowercase, plural)."""
        return inflection.pluralize(inflection.underscore(cls.__name__))


class ClientTable(Base):
    """ORM model for clients data."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    age = mapped_column(Integer, nullable=True)
    gender = mapped_column(String(20), nullable=True)
    net_worth: Mapped[float] = mapped_column(Float, nullable=True)

    transactions = relationship("TransactionTable", back_populates="client")

    __table_args__ = (
        Index("ix_clients_net_worth", "net_worth"),
        Index("ix_clients_age", "age"),
    )

    def __repr__(self) -> str:
        return f"<ClientTable(id={self.id}, net_worth={self.net_worth})>"


class TransactionTable(Base):
    """ORM model for transactions data."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id = mapped_column(
        String(36),
        ForeignKey("client_tables.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_service = mapped_column(String(100), nullable=False, index=True)
    raw_payment_method = mapped_column(String(50), nullable=False)

    transaction_date = mapped_column(DateTime, nullable=True, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    city = mapped_column(String(100), nullable=True)
    consultant = mapped_column(String(100), nullable=True)

    service_category = mapped_column(String(50), nullable=False, index=True)
    payment_method_category = mapped_column(String(50), nullable=False)

    client = relationship("ClientTable", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_date_amount", "transaction_date", "amount"),
        Index("ix_transactions_client_date", "client_id", "transaction_date"),
    )

    def __repr__(self) -> str:
        return f"<TransactionTable(id={self.id}, amount={self.amount})>"


class AnalysisResultTable(Base):
    """Store analysis results for quick access."""

    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_name = mapped_column(String(100), nullable=False, index=True)
    result_json = mapped_column(String, nullable=False)
    created_at = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    parameters = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<AnalysisResultTable(id={self.id}, "
            f"analysis_name={self.analysis_name}, "
            f"result_json={self.result_json}, "
            f"created_at={self.created_at}, "
            f"parameters={self.parameters})>"
        )
