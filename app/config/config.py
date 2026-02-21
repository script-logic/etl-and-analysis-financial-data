"""
Configuration module for the application.

Provides type-safe settings using Pydantic.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infrastructure.logger.interfaces import ILoggingConfig


class LoggingConfig(BaseSettings):
    """Configuration for the logging system."""

    app_name: str = "Finance Analysis"
    debug: bool = True  # if True then color console render, else json render
    log_level: str = "INFO"
    enable_file_logging: bool = False
    logs_dir: Path = Path("logs")
    logs_file_name: str = "app.log"
    max_file_size_mb: int = 10
    backup_count: int = 5


class DataPathsConfig(BaseSettings):
    """Configuration for data file paths."""

    transactions_file: Path = Field(
        default=Path("data/transactions_data.xlsx"),
        description="Path to transactions Excel file",
    )
    clients_file: Path = Field(
        default=Path("data/clients_data.json"),
        description="Path to clients JSON file",
    )
    database_file: Path = Field(
        default=Path("warehouse.db"),
        description="Path to SQLite database",
    )
    reports_dir: Path = Field(
        default=Path("reports"),
        description="Directory for reports and visualizations",
    )
    data_hashes_file: Path = Field(
        default=Path(".data_hashes.json"),
        description="File to store data file hashes",
    )

    @field_validator("reports_dir", mode="after")
    @classmethod
    def create_reports_dir(cls, v: Path) -> Path:
        """Ensure reports directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("transactions_file", "clients_file", mode="after")
    @classmethod
    def validate_data_files(cls, v: Path) -> Path:
        """Validate that data files exist."""
        if not v.exists():
            raise FileNotFoundError(f"Data file not found: {v}")
        return v


class AnalysisConfig(BaseSettings):
    """Configuration for analysis parameters."""

    top_services_limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of top services to display",
    )
    forecast_months: int = Field(
        default=1,
        ge=1,
        le=12,
        description="Number of months to forecast",
    )
    min_transactions_for_forecast: int = Field(
        default=3,
        ge=1,
        description="Minimum months of data required for forecast",
    )


class AppConfig(BaseSettings):
    """Main application configuration."""

    data_paths: DataPathsConfig = Field(default_factory=DataPathsConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    logger: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_nested_delimiter="__",
    )

    @property
    def logger_adapter(self) -> ILoggingConfig:
        """
        Create logging configuration adapter from settings.

        Returns:
            ILoggingConfig: Configuration object for the logging system.
        """
        return LoggingConfig(
            debug=self.logger.debug,
            app_name=self.logger.app_name,
            log_level=self.logger.log_level.upper(),
            enable_file_logging=self.logger.enable_file_logging,
            logs_dir=self.logger.logs_dir,
            logs_file_name=self.logger.logs_file_name,
            max_file_size_mb=self.logger.max_file_size_mb,
            backup_count=self.logger.backup_count,
        )


@lru_cache
def get_config() -> AppConfig:
    config = AppConfig()
    return config
