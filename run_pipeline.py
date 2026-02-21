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
from typing import Optional

from structlog import get_logger

from app.application.use_cases.build_warehouse import build_warehouse
from app.application.use_cases.run_analysis import run_analysis
from app.config import get_config
from app.infrastructure.logger.manager import setup_logging


def setup_arg_parser() -> argparse.ArgumentParser:
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
        default=Path("data/transactions_data.xlsx"),
        help="Path to transactions Excel file",
    )
    parser.add_argument(
        "--clients",
        type=Path,
        default=Path("data/clients_data.json"),
        help="Path to clients JSON file",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("warehouse.db"),
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--forecast-months",
        type=int,
        default=1,
        help="Number of months to forecast (default: 1)",
    )
    parser.add_argument(
        "--min-months-forecast",
        type=int,
        default=3,
        help="Minimum months required for forecast (default: 3)",
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
    hash_file: Path = Path(".data_hashes.json"),
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
        with open(hash_file, "r") as f:
            saved_hashes = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return True

    if current_hashes != saved_hashes:
        with open(hash_file, "w") as f:
            json.dump(current_hashes, f)
        return True

    return False


def main() -> Optional[int]:
    """Main pipeline execution."""
    config = get_config()
    setup_logging(config.logger_adapter)
    logger = get_logger(__name__)

    parser = setup_arg_parser()
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("ФИНАНСОВЫЙ АНАЛИЗ - ПАЙПЛАЙН")
    print("=" * 80)

    if args.no_clear:
        should_clear = False
    elif args.clear_db:
        should_clear = True
    else:
        should_clear = should_clear_database(args.transactions, args.clients)
        if should_clear:
            print("\n Автоматическая очистка БД (файлы данных изменились)")
        else:
            print("\n Используем существующую БД (файлы не менялись)")

    if not check_data_files(args.transactions, args.clients):
        return 1

    try:
        print("\n ЭТАП 1: ЗАГРУЗКА ДАННЫХ В ХРАНИЛИЩЕ")
        print("-" * 40)

        load_results = build_warehouse(
            transactions_path=args.transactions,
            clients_path=args.clients,
            db_path=args.db,
            clear=should_clear,
        )

        print(
            f"   Загружено транзакций: {load_results['transactions_loaded']}"
        )
        print(f"   Загружено клиентов: {load_results['clients_loaded']}")

        print("\n ЭТАП 2: АНАЛИЗ ДАННЫХ")
        print("-" * 40)

        analysis_results = run_analysis(
            db_path=args.db,
            generate_plots=not args.no_plots,
            forecast_months=args.forecast_months,
            min_months_for_forecast=args.min_months_forecast,
        )

        print("\n ЭТАП 3: СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
        print("-" * 40)

        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = reports_dir / f"analysis_results_{timestamp}.json"

        def json_serializer(obj):
            if isinstance(obj, Path):
                return str(obj)
            raise TypeError(f"Type {type(obj)} not serializable")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                analysis_results,
                f,
                indent=2,
                default=json_serializer,
                ensure_ascii=False,
            )

        print(f"  Результаты сохранены: {json_path}")

        if not args.no_plots:
            print("  Визуализации сохранены в папке: reports/")

        print("\n" + "=" * 80)
        print(" ПАЙПЛАЙН УСПЕШНО ЗАВЕРШЕН")
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.exception("Pipeline failed")
        print(f"\n ОШИБКА: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
