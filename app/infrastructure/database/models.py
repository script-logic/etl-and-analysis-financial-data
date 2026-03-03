"""
SQLAlchemy ORM models for the warehouse database.

These models represent the cleaned and normalized data structure.
"""

from datetime import datetime

import inflection
from sqlalchemy import (
    JSON,
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

    def __repr__(self) -> str:
        """Provide a basic representation for all models."""
        attrs = []
        for key in self.__mapper__.columns.keys():
            if hasattr(self, key):
                attrs.append(f"{key}={getattr(self, key)!r}")
        return f"<{self.__class__.__name__}({', '.join(attrs)})>"


class ClientTable(Base):
    """ORM model for clients data."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=True)
    net_worth: Mapped[float] = mapped_column(Float, nullable=True)

    transactions = relationship("TransactionTable", back_populates="client")

    __table_args__ = (
        Index("ix_clients_net_worth", "net_worth"),
        Index("ix_clients_age", "age"),
    )


class TransactionTable(Base):
    """ORM model for transactions data."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(f"{ClientTable.__tablename__}.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    raw_service: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    raw_payment_method: Mapped[str] = mapped_column(String(50), nullable=False)

    transaction_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=True, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    consultant: Mapped[str] = mapped_column(String(100), nullable=True)

    service_category: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    payment_method_category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )

    client = relationship("ClientTable", back_populates="transactions")

    __table_args__ = (
        Index("ix_transactions_date_amount", "transaction_date", "amount"),
        Index("ix_transactions_client_date", "client_id", "transaction_date"),
    )


class AnalysisResultTable(Base):
    """Store analysis results for quick access."""

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    analysis_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index(
            "ix_analysis_results_name_created", "analysis_name", "created_at"
        ),
    )
