"""
Main pipeline script.

Usage:
    python run_pipeline.py [--no-plots] [--clear-db] [--forecast-months N]
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

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
    print("\n" + "_" * 80 + "\n")
    print("📊 ФИНАНСОВЫЙ АНАЛИЗ - РЕЗУЛЬТАТЫ 📊".center(80))
    print("_" * 80)

    print("\n🏆 ТОП-5 УСЛУГ ПО КОЛИЧЕСТВУ ЗАКАЗОВ:")
    for i, s in enumerate(results["top_services"], 1):
        print(f"   {i}. {s['service']}: {s['count']} заказов")

    if results["max_revenue_service"]:
        print("\n💰 УСЛУГА С МАКСИМАЛЬНОЙ ВЫРУЧКОЙ:")
        print(
            f"   {results['max_revenue_service']['service']}: "
            f"{results['max_revenue_service']['revenue']:,.2f}"
        )

    print("\n💳 РАСПРЕДЕЛЕНИЕ ПО СПОСОБАМ ОПЛАТЫ:")
    for i, (method, pct) in enumerate(results["payment_methods"].items(), 1):
        print(f"   {i}. {method}: {pct}%")

    print("\n💵 ВЫРУЧКА ЗА ПОСЛЕДНИЙ МЕСЯЦ:")
    print(f"   {results['last_month_revenue']:,.2f}")

    print("\n👥 АНАЛИЗ ПО СЕГМЕНТАМ КЛИЕНТОВ:")
    for i, segment in enumerate(results["client_segments"]):
        medal = (
            "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
        )
        print(f"  {medal} {segment['segment']}:")
        print(f"       Клиентов: {segment['client_count']}")
        print(f"       Выручка: {segment['total_revenue']:,.2f}")
        print(f"       Транзакций: {segment['transaction_count']}")
        print(f"       Средний чек: {segment['avg_transaction']:,.2f}")

    forecast = results.get("forecast", {})
    if forecast.get("available", False):
        print("\n🔮 ПРОГНОЗ НА СЛЕДУЮЩИЙ МЕСЯЦ:")

        if forecast.get("count_forecast"):
            trend = forecast.get("count_trend", "stable")
            trend_emoji = {
                "increasing": "📈",
                "decreasing": "📉",
                "stable": "📊",
            }.get(trend, "📊")
            trend_str = {
                "increasing": "Рост",
                "decreasing": "Падение",
                "stable": "Стабильно",
            }.get(trend, "")
            print(
                f"   {trend_emoji} Транзакций: "
                f"{forecast['count_forecast'][0]} "
                f"({trend_str})"
            )

        if forecast.get("revenue_forecast"):
            trend = forecast.get("revenue_trend", "stable")
            trend_emoji = {
                "increasing": "📈",
                "decreasing": "📉",
                "stable": "📊",
            }.get(trend, "📊")
            trend_str = {
                "increasing": "Рост",
                "decreasing": "Падение",
                "stable": "Стабильно",
            }.get(trend, "")
            print(
                f"   {trend_emoji} Выручка: "
                f"{forecast['revenue_forecast'][0]:,.2f} ({trend_str})"
            )

        if "metrics" in forecast:
            r2 = forecast["metrics"].get("count_r2")
            if r2:
                quality_emoji = (
                    "🟢" if r2 > 0.7 else "🟡" if r2 > 0.3 else "🔴"
                )
                quality = (
                    "хорошее"
                    if r2 > 0.7
                    else "среднее"
                    if r2 > 0.3
                    else "слабое"
                )
                print(
                    f"   ❓ Качество прогноза (R²): {r2:.3f} "
                    f"{quality_emoji} ({quality})"
                )
    else:
        print("\n🔮 ПРОГНОЗ:")
        print(f"  ⚠️ {forecast.get('message', 'Прогноз недоступен')}")

    if "report" in results:
        report_info = results["report"]
        print("\n" + "_" * 80)
        print("\nОТЧЁТЫ СОЗДАНЫ:")
        print(f"  📄 Markdown: {report_info['markdown']}")
        print(f"  📊 JSON: {report_info['json']}")
        print(f"  📁 Папка: {report_info['folder']}")

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

        logger.info("STAGE 3: REPORT GENERATION")

        print_summary(analysis_results)

        return 0

    except Exception as e:
        logger.exception("Pipeline failed")
        logger.error(f"{e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
