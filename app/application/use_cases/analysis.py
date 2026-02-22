"""
Analysis use case: Run all required analyses and generate reports.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
from structlog import get_logger

from app.infrastructure.analysis import (
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
        warehouse: Warehouse,
        viz_service: Optional[VisualizationService] = None,
        forecast_months: int = 1,
        min_months_for_forecast: int = 3,
    ):
        """
        Initialize analysis use case.

        Args:
            warehouse: Database warehouse instance.
            viz_service: Visualization service (optional).
            forecast_months: Number of months to forecast.
            min_months_for_forecast: Minimum months required for forecast.
        """
        self.warehouse = warehouse
        self.viz_service = viz_service or VisualizationService()
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
                results["visualizations"] = viz_results

            if save_results:
                analysis_repo.save_result(
                    "full_analysis",
                    results,
                    {"timestamp": datetime.now().isoformat()},
                )
                session.commit()
                logger.info("Saved analysis results to database")

            self._print_summary(results)

            return results

        finally:
            session.close()

    def _generate_visualizations(self, session) -> Dict[str, str]:
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
            merged_df.groupby("age")["amount"]
            .agg(["mean", "count"])
            .reset_index()
            .rename(
                columns={"mean": "avg_amount", "count": "transaction_count"}
            )
        )

        age_data: list[Dict[str, Any]] = []
        for _, row in age_df.iterrows():
            age_data.append(
                {
                    "age": int(row["age"]) if pd.notna(row["age"]) else 0,
                    "avg_amount": float(row["avg_amount"]),
                    "transaction_count": int(row["transaction_count"]),
                }
            )

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

    def _print_summary(self, results: Dict[str, Any]) -> None:
        """Print analysis summary to console."""
        print("\n" + "=" * 80)
        print("АНАЛИЗ ДАННЫХ - РЕЗУЛЬТАТЫ")
        print("=" * 80)

        print("\nТОП-5 УСЛУГ ПО КОЛИЧЕСТВУ:")
        for i, s in enumerate(results["top_services"], 1):
            print(f"  {i}. {s['service']}: {s['count']} заказов")

        if results["max_revenue_service"]:
            print("\nУСЛУГА С МАКС. ВЫРУЧКОЙ:")
            print(
                f"{results['max_revenue_service']['service']}: "
                f"{results['max_revenue_service']['revenue']:,.2f}"
            )

        print("\nРАСПРЕДЕЛЕНИЕ ПО СПОСОБАМ ОПЛАТЫ:")
        for method, pct in results["payment_methods"].items():
            print(f"{method}: {pct}%")

        print(
            f"\nВЫРУЧКА ЗА ПОСЛЕДНИЙ МЕСЯЦ: "
            f"{results['last_month_revenue']:,.2f}"
        )

        print("\nАНАЛИЗ ПО СЕГМЕНТАМ КЛИЕНТОВ:")
        for segment in results["client_segments"]:
            print(f"{segment['segment']}:")
            print(f"  Клиентов: {segment['client_count']}")
            print(f"  Выручка: {segment['total_revenue']:,.2f}")
            print(f"  Транзакций: {segment['transaction_count']}")
            print(f"  Средний чек: {segment['avg_transaction']:,.2f}")

        forecast = results.get("forecast", {})
        if forecast.get("available", False):
            print("\nПРОГНОЗ НА СЛЕДУЮЩИЙ МЕСЯЦ:")
            if forecast.get("count_forecast"):
                trend = forecast.get("count_trend", "stable")
                trend_str = {
                    "increasing": "Рост.",
                    "decreasing": "Падение.",
                    "stable": "Боковик.",
                }.get(trend, "")
                print(
                    f"  {trend_str} Транзакций: "
                    f"{forecast['count_forecast'][0]}"
                )
            if forecast.get("revenue_forecast"):
                trend = forecast.get("revenue_trend", "stable")
                trend_str = {
                    "increasing": "Рост.",
                    "decreasing": "Падение.",
                    "stable": "Боковик.",
                }.get(trend, "")
                print(
                    f"  {trend_str} Выручка: "
                    f"{forecast['revenue_forecast'][0]:,.2f}"
                )
            if "metrics" in forecast:
                r2 = forecast["metrics"].get("count_r2")
                if r2:
                    quality = (
                        "хорошее"
                        if r2 > 0.7
                        else "среднее" if r2 > 0.3 else "слабое"
                    )
                    print(f"  Качество прогноза (R²): {r2:.3f} ({quality})")
        else:
            print("\nПРОГНОЗ:")
            print(f"  {forecast.get('message', 'Прогноз недоступен')}")

        print("\n" + "=" * 80)


def run_analysis(
    db_path: Path | str = "warehouse.db",
    generate_plots: bool = True,
    forecast_months: int = 1,
    min_months_for_forecast: int = 3,
) -> Dict[str, Any]:
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
        warehouse,
        forecast_months=forecast_months,
        min_months_for_forecast=min_months_for_forecast,
    )

    try:
        return use_case.execute(generate_plots=generate_plots)
    finally:
        warehouse.close()
