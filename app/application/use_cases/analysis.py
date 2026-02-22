"""
Analysis use case: Run all required analyses and generate reports.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
import pandas as pd
from structlog import get_logger

from app.config import AppConfig
from app.infrastructure.analysis import (
    ReportService,
    VisualizationService,
    create_demand_forecast,
)
from app.infrastructure.database import (
    AnalysisRepository,
    ClientRepository,
    ClientTable,
    TransactionRepository,
    TransactionTable,
    Warehouse,
    create_warehouse,
)

logger = get_logger(__name__)


class RunAnalysisUseCase:
    """
    Run all analyses.

    Produces:
    1. Top 5 services by order count
    2. Average amount by city
    3. Service with max revenue
    4. Payment method distribution (%)
    5. Last month revenue
    6. Client segmentation analysis
    7. Visualizations
    8. Forecast
    """

    def __init__(
        self,
        config: AppConfig,
        warehouse: Warehouse,
        viz_service: VisualizationService | None = None,
        report_service: ReportService | None = None,
        forecast_months: int = 1,
        min_months_for_forecast: int = 3,
    ):
        """
        Initialize analysis use case.

        Args:
            warehouse: Database warehouse instance.
            viz_service: Visualization service (optional).
            report_service: Report service (optional).
            forecast_months: Number of months to forecast.
            min_months_for_forecast: Minimum months required for forecast.
        """
        self.warehouse = warehouse
        self.viz_service = viz_service or VisualizationService(
            config.data_paths.reports_dir
        )
        self.report_service = report_service or ReportService(
            config.data_paths.reports_dir
        )
        self.forecast_months = forecast_months
        self.min_months_for_forecast = min_months_for_forecast

    def execute(
        self,
        generate_plots: bool = True,
        save_results: bool = True,
    ) -> dict[str, Any]:
        """
        Run all analyses.

        Args:
            generate_plots: Whether to generate visualizations.
            save_results: Whether to save results to database.

        Returns:
            Dict with all analysis results.
        """
        logger.info("Starting data analysis")

        if generate_plots:
            report_dir, metadata_dir = (
                self.report_service.create_report_folder()
            )
            self.viz_service = VisualizationService(metadata_dir)
        else:
            report_dir, metadata_dir = (
                self.report_service.create_report_folder()
            )
        session = self.warehouse.get_session()

        try:
            transaction_repo = TransactionRepository(session)
            client_repo = ClientRepository(session)
            analysis_repo = AnalysisRepository(session)

            results: dict[str, Any] = {}

            logger.info("Calculating top 5 services...")
            results["top_services"] = (
                transaction_repo.get_top_services_by_count(5)
            )

            logger.info("Calculating average amount by city...")
            results["avg_by_city"] = transaction_repo.get_avg_amount_by_city()

            logger.info("Finding service with max revenue...")
            results["max_revenue_service"] = (
                transaction_repo.get_service_with_max_revenue()
            )

            logger.info("Calculating payment method distribution...")
            results["payment_methods"] = (
                transaction_repo.get_payment_method_distribution()
            )

            logger.info("Calculating last month revenue...")
            results["last_month_revenue"] = (
                transaction_repo.get_last_month_revenue()
            )

            logger.info("Analyzing client segments...")
            results["client_segments"] = (
                client_repo.get_detailed_revenue_by_segment()
            )

            logger.info("Running additional analyses...")
            results["service_performance"] = (
                transaction_repo.get_service_performance()
            )
            results["service_performance"] = (
                transaction_repo.enrich_with_percentages(
                    results["service_performance"]
                )
            )

            logger.info("Calculating monthly trend...")
            results["monthly_trend"] = (
                transaction_repo.get_monthly_revenue_trend(12)
            )

            results["clients_without_transactions"] = (
                client_repo.get_clients_without_transactions()
            )

            logger.info("Generating demand forecast...")
            forecast = create_demand_forecast(
                monthly_data=results["monthly_trend"],
                forecast_months=self.forecast_months,
                min_months=self.min_months_for_forecast,
            )
            results["forecast"] = forecast

            if generate_plots:
                logger.info("Generating visualizations...")
                viz_results = self._generate_visualizations(session)
                json_path = self._save_json_results(results, metadata_dir)
                viz_results["json_data"] = str(json_path)
                md_path = self.report_service.save_markdown_report(
                    results, viz_results
                )
                results["report"] = {
                    "markdown": str(md_path),
                    "folder": str(report_dir),
                    "json": str(json_path),
                    "visualizations": viz_results,
                }

                logger.info(f"Report generated: {md_path}")
                results["visualizations"] = viz_results

            if save_results:
                analysis_repo.save_result(
                    "full_analysis",
                    results,
                    {"timestamp": datetime.now().isoformat()},
                )
                session.commit()
                logger.info("Saved analysis results to database")

            return results

        finally:
            session.close()

    def _save_json_results(
        self,
        results: dict[str, Any],
        output_dir: Path,
    ) -> Path:
        """Save analysis results as JSON."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"analysis_results_{timestamp}.json"

        def json_serializer(obj):
            if isinstance(obj, Path):
                return str(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(json_path, "w", encoding="utf-8") as f:
            json_bytes = orjson.dumps(
                results,
                default=json_serializer,
                option=orjson.OPT_INDENT_2,
            )
            f.write(json_bytes.decode("utf-8"))

        logger.info(f"Saved JSON results: {json_path}")
        return json_path

    def _generate_visualizations(self, session) -> dict[str, str]:
        """
        Generate all visualizations.

        Returns:
            Dict mapping plot names to file paths.
        """
        transactions_query = session.query(TransactionTable)
        clients_query = session.query(ClientTable)

        transactions_df = pd.read_sql(
            transactions_query.statement, session.bind
        )
        clients_df = pd.read_sql(clients_query.statement, session.bind)

        merged_df = pd.merge(
            transactions_df,
            clients_df[["id", "age", "net_worth"]],
            left_on="client_id",
            right_on="id",
            how="inner",
        )

        viz_results = {}

        path = self.viz_service.plot_transaction_distribution(
            transactions_df["amount"].tolist()
        )
        viz_results["distribution"] = str(path)

        path = self.viz_service.plot_revenue_by_service(
            self._get_service_data(session)
        )
        viz_results["revenue_by_service"] = str(path)

        age_df = (
            merged_df
            .groupby("age")["amount"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(
                columns={"mean": "avg_amount", "count": "transaction_count"}
            )
        )

        age_data: list[dict[str, Any]] = []
        for _, row in age_df.iterrows():
            age_data.append({
                "age": int(row["age"]) if pd.notna(row["age"]) else 0,
                "avg_amount": float(row["avg_amount"]),
                "transaction_count": int(row["transaction_count"]),
            })

        path = self.viz_service.plot_revenue_by_age(age_data)
        viz_results["revenue_by_age"] = str(path)

        monthly_repo = TransactionRepository(session)
        monthly_data = monthly_repo.get_monthly_revenue_trend()
        path = self.viz_service.plot_monthly_trend(monthly_data)
        viz_results["monthly_trend"] = str(path)

        path = self.viz_service.generate_report(transactions_df, clients_df)
        viz_results["html_report"] = str(path)

        return viz_results

    def _get_service_data(self, session) -> list:
        """Get service performance data for visualization."""
        repo = TransactionRepository(session)
        return repo.get_service_performance()


def run_analysis(
    config: AppConfig,
    db_path: Path | str,
    generate_plots: bool = True,
    forecast_months: int = 1,
    min_months_for_forecast: int = 3,
) -> dict[str, Any]:
    """
    Run analysis with default configuration.

    Args:
        db_path: Path to SQLite database.
        generate_plots: Whether to generate visualizations.
        forecast_months: Number of months to forecast.
        min_months_for_forecast: Minimum months required for forecast.

    Returns:
        Dict with all analysis results.
    """
    warehouse = create_warehouse(db_path)
    use_case = RunAnalysisUseCase(
        config,
        warehouse,
        forecast_months=forecast_months,
        min_months_for_forecast=min_months_for_forecast,
    )

    try:
        return use_case.execute(generate_plots=generate_plots)
    finally:
        warehouse.close()
