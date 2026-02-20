"""
Database warehouse initialization and session management.
"""

import logging
from pathlib import Path
from typing import Any
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.models import Base

logger = logging.getLogger(__name__)


class Warehouse:
    """
    Database warehouse manager.

    Handles SQLite connection and session lifecycle.
    """

    def __init__(self, db_path: Path | str = "warehouse.db"):
        """
        Initialize warehouse connection.

        Args:
            db_path: Path to SQLite database file.
                   Use ":memory:" for in-memory database.
        """
        self.db_path = str(db_path)
        self.engine: Engine | None = None
        self.SessionLocal: sessionmaker[Session] | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Create engine and session factory."""
        connect_args: dict[Any, Any] = {
            "check_same_thread": False,  # Allow multi-threaded access
            "timeout": 15,  # Wait up to 15s for lock
        }

        # For in-memory database with shared cache
        if self.db_path == ":memory:":
            connect_args["url"] = True
            connect_args["cached"] = "shared"

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args=connect_args,
            echo=False,
            poolclass=StaticPool,
            future=True,
        )

        Base.metadata.create_all(self.engine)

        self.SessionLocal = sessionmaker(
            bind=self.engine,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )

        logger.info(f"Warehouse initialized at {self.db_path}")

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            SQLAlchemy Session object
        """
        if not self.SessionLocal:
            raise RuntimeError("Warehouse not properly initialized")
        return self.SessionLocal()

    def close(self) -> None:
        """Close database connection."""
        if self.engine:
            self.engine.dispose()
            logger.info("Warehouse connection closed")

    def clear_all(self) -> None:
        """Clear all data from database (for testing)."""
        if self.engine:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)
        logger.warning("All warehouse data cleared")


def create_warehouse(db_path: Path | str = "warehouse.db") -> Warehouse:
    """Create and return a Warehouse instance."""
    return Warehouse(db_path)
