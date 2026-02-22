"""
Main pipeline script.

Usage:
    python run_pipeline.py [--no-plots] [--clear-db] [--forecast-months N]
"""

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import orjson
from structlog import get_logger

from app.application.use_cases import build_warehouse, run_analysis
from app.config import AppConfig, get_config
from app.infrastructure.logger import setup_logging


def setup_arg_parser(config: AppConfig) -> argparse.ArgumentParser:
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Run ETL and analysis pipeline for financial data"
    )
    parser.add_argument(
        "--no-plots",
        action="store_true",
        help="Skip generating visualizations",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear database (keep existing data)",
    )
    parser.add_argument(
        "--clear-db", action="store_true", help="Clear database before loading"
    )
    parser.add_argument(
        "--transactions",
        type=Path,
        default=Path(config.data_paths.transactions_file),
        help="Path to transactions Excel file",
    )
    parser.add_argument(
        "--clients",
        type=Path,
        default=Path(config.data_paths.clients_file),
        help="Path to clients JSON file",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path(config.data_paths.database_file),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--forecast-months",
        type=int,
        default=config.analysis.forecast_months,
        help="Number of months to forecast",
    )
    parser.add_argument(
        "--min-months-forecast",
        type=int,
        default=config.analysis.min_months_for_forecast,
        help="Minimum months required for forecast",
    )
    return parser


def check_data_files(transactions_path: Path, clients_path: Path) -> bool:
    """Check if data files exist."""
    missing = []

    if not transactions_path.exists():
        missing.append(f"Transactions file: {transactions_path}")

    if not clients_path.exists():
        missing.append(f"Clients file: {clients_path}")

    if missing:
        print("\nMissing data files:")
        for m in missing:
            print(f"  - {m}")
        print("\nPlease place the data files in the correct locations.")
        return False

    return True


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def should_clear_database(
    transactions_path: Path,
    clients_path: Path,
    hash_file: Path,
) -> bool:
    """
    Check if data files have changed since last run.

    Returns:
        True if database should be cleared, False otherwise.
    """
    current_hashes = {
        "transactions": get_file_hash(transactions_path),
        "clients": get_file_hash(clients_path),
    }

    if not hash_file.exists():
        with open(hash_file, "w") as f:
            json.dump(current_hashes, f)
        return True

    try:
        with open(hash_file) as f:
            saved_hashes = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return True

    if current_hashes != saved_hashes:
        with open(hash_file, "w") as f:
            json.dump(current_hashes, f)
        return True

    return False


def print_summary(results: dict[str, Any]) -> None:
    """Print analysis summary to console."""
    print("\n" + "_" * 80)
    print("\nАНАЛИЗ ДАННЫХ - РЕЗУЛЬТАТЫ")
    print("_" * 80)

    print("\nТОП-5 УСЛУГ ПО КОЛИЧЕСТВУ:")
    for i, s in enumerate(results["top_services"], 1):
        print(f"  {i}. {s['service']}: {s['count']} заказов")

    if results["max_revenue_service"]:
        print("\nУСЛУГА С МАКСИМАЛЬНОЙ ВЫРУЧКОЙ:")
        print(
            f"  {results['max_revenue_service']['service']}: "
            f"{results['max_revenue_service']['revenue']:,.2f}"
        )

    print("\nРАСПРЕДЕЛЕНИЕ ПО СПОСОБАМ ОПЛАТЫ:")
    for method, pct in results["payment_methods"].items():
        print(f"  {method}: {pct}%")

    print("\nВЫРУЧКА ЗА ПОСЛЕДНИЙ МЕСЯЦ:")
    print(f"  {results['last_month_revenue']:,.2f}")

    print("\nАНАЛИЗ ПО СЕГМЕНТАМ КЛИЕНТОВ:")
    for segment in results["client_segments"]:
        print(f"  {segment['segment']}:")
        print(f"    Клиентов: {segment['client_count']}")
        print(f"    Выручка: {segment['total_revenue']:,.2f}")
        print(f"    Транзакций: {segment['transaction_count']}")
        print(f"    Средний чек: {segment['avg_transaction']:,.2f}")

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
            print(f"  {trend_str} Транзакций: {forecast['count_forecast'][0]}")
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
                    else "среднее"
                    if r2 > 0.3
                    else "слабое"
                )
                print(f"  Качество прогноза (R²): {r2:.3f} ({quality})")
    else:
        print("\nПРОГНОЗ:")
        print(f"  {forecast.get('message', 'Прогноз недоступен')}")

    print("\n" + "_" * 80)
    print("\n")


def main() -> int | None:
    """Main pipeline execution."""
    config = get_config()
    setup_logging(config.logger_adapter)
    logger = get_logger("run_pipeline.py")

    parser = setup_arg_parser(config)
    args = parser.parse_args()

    logger.info("=== START PIPELINE ===")

    if args.no_clear:
        should_clear = False
    elif args.clear_db:
        should_clear = True
    else:
        should_clear = should_clear_database(
            args.transactions, args.clients, config.data_paths.data_hashes_file
        )
        if should_clear:
            logger.info("Automatic database cleanup (data files have changed)")

    if not check_data_files(args.transactions, args.clients):
        return 1

    try:
        logger.info("STAGE 1: LOADING DATA INTO THE STORAGE")

        if should_clear or not config.data_paths.database_file.exists():
            load_results = build_warehouse(
                transactions_path=args.transactions,
                clients_path=args.clients,
                db_path=args.db,
                clear=should_clear,
            )

            logger.info(
                f"Transactions loaded: {load_results['transactions_loaded']}"
            )
            logger.info(f"Clients loaded: {load_results['clients_loaded']}")
        else:
            logger.info("Files haven't changed. Using existing database.")

        logger.info("STAGE 2: DATA ANALYSIS")

        analysis_results = run_analysis(
            config,
            db_path=args.db,
            generate_plots=not args.no_plots,
            forecast_months=args.forecast_months,
            min_months_for_forecast=args.min_months_forecast,
        )

        logger.info("STAGE 3: SAVING RESULTS")

        reports_dir = config.data_paths.reports_dir
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = (
            reports_dir
            / f"{config.data_paths.analysis_results_json_file_prefix}"
            f"{timestamp}.json"
        )

        def json_serializer(obj):
            if isinstance(obj, Path):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(json_path, "w", encoding="utf-8") as f:
            json_bytes = orjson.dumps(
                analysis_results,
                default=json_serializer,
                option=orjson.OPT_INDENT_2,
            )
            f.write(json_bytes.decode("utf-8"))

        logger.info(f"Results saved to file: {json_path}")

        if not args.no_plots:
            logger.info(f"Visualizations saved to folder: {reports_dir}")

        logger.info("PIPELINE COMPLETED SUCCESSFULLY")

        print_summary(analysis_results)

        return 0

    except Exception as e:
        logger.exception("Pipeline failed")
        logger.error(f"{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
