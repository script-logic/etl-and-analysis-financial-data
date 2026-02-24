"""
Service for organizing analysis reports with proper folder structure.
"""

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from structlog import get_logger

logger = get_logger(__name__)


class ReportService:
    """
    Manages report generation with timestamped folders.

    Creates structure:
    reports/
    ├── report_20260223_010453/
    │   ├── REPORT.md
    │   └── report_metadata/
    │       ├── analysis_report.html
    │       ├── analysis_results_20260223_010453.json
    │       ├── monthly_trend.png
    │       ├── revenue_by_age.png
    │       ├── revenue_by_service.png
    │       └── transaction_distribution.png
    """

    def __init__(self, base_reports_dir: Path) -> None:
        """
        Initialize report service.

        Args:
            base_reports_dir: Base directory for all reports.
        """
        self.base_reports_dir = Path(base_reports_dir)
        self.base_reports_dir.mkdir(parents=True, exist_ok=True)

        self.timestamp: str | None = None
        self.report_dir: Path | None = None
        self.metadata_dir: Path | None = None

    def create_report_folder(self) -> tuple[Path, Path]:
        """
        Create a new timestamped report folder structure.

        Returns:
            Tuple of (report_dir, metadata_dir)
        """
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_dir = self.base_reports_dir / f"report_{self.timestamp}"
        self.metadata_dir = self.report_dir / "report_metadata"

        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created report folder: {self.report_dir}")
        return self.report_dir, self.metadata_dir

    def save_markdown_report(
        self,
        analysis_results: dict[str, Any],
        viz_paths: Mapping[str, Path | str],
    ) -> Path:
        """
        Generate and save Markdown report with embedded references to plots.

        Args:
            analysis_results: Dictionary with analysis results.
            viz_paths: Dictionary mapping plot names to file paths.

        Returns:
            Path to the saved Markdown file.
        """
        if not self.report_dir or not self.metadata_dir:
            raise RuntimeError("Call create_report_folder() first")

        md_lines: list[str] = []
        md_lines.append("# Финансовый анализ - Отчет")
        md_lines.append("")
        md_lines.append(f"**Дата отчета:** {self._format_timestamp()}")
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

        md_lines.append("## Топ-5 услуг по количеству заказов")
        md_lines.append("")
        for i, s in enumerate(analysis_results.get("top_services", []), 1):
            md_lines.append(f"{i}. **{s['service']}**: {s['count']} заказов")
        md_lines.append("")

        max_rev = analysis_results.get("max_revenue_service")
        if max_rev:
            md_lines.append("## Услуга с максимальной выручкой")
            md_lines.append("")
            md_lines.append(
                f"**{max_rev['service']}**: {max_rev['revenue']:,.2f}"
            )
            md_lines.append("")

        md_lines.append("## Средняя сумма транзакций по городам")
        md_lines.append("")

        avg_by_city = analysis_results.get("avg_by_city", [])
        if avg_by_city:
            for item in avg_by_city[:]:
                md_lines.append(
                    f"- **{item['city']}**: {item['avg_amount']:,.2f}"
                )
        else:
            md_lines.append("_Нет данных по городам_")
        md_lines.append("")

        md_lines.append("## Распределение по способам оплаты")
        md_lines.append("")
        for method, pct in analysis_results.get("payment_methods", {}).items():
            md_lines.append(f"- **{method}**: {pct}%")
        md_lines.append("")

        md_lines.append("## Выручка за последний месяц")
        md_lines.append("")
        md_lines.append(
            f"**{analysis_results.get('last_month_revenue', 0):,.2f}**"
        )
        md_lines.append("")

        md_lines.append("## Анализ по сегментам клиентов")
        md_lines.append("")
        for segment in analysis_results.get("client_segments", []):
            md_lines.append(f"### {segment['segment']}")
            md_lines.append(f"- Клиентов: {segment['client_count']}")
            md_lines.append(f"- Выручка: {segment['total_revenue']:,.2f}")
            md_lines.append(f"- Транзакций: {segment['transaction_count']}")
            md_lines.append(
                f"- Средний чек: {segment['avg_transaction']:,.2f}"
            )
            md_lines.append("")

        forecast = analysis_results.get("forecast", {})
        if forecast.get("available", False):
            md_lines.append("## Прогноз на следующий месяц")
            md_lines.append("")

            if forecast.get("count_forecast"):
                trend = forecast.get("count_trend", "stable")
                trend_str = {
                    "increasing": "📈 Рост",
                    "decreasing": "📉 Падение",
                    "stable": "➡️ Стабильно",
                }.get(trend, "")
                md_lines.append(
                    f"- **Транзакции**: {forecast['count_forecast'][0]} "
                    f"({trend_str})"
                )

            if forecast.get("revenue_forecast"):
                trend = forecast.get("revenue_trend", "stable")
                trend_str = {
                    "increasing": "📈 Рост",
                    "decreasing": "📉 Падение",
                    "stable": "➡️ Стабильно",
                }.get(trend, "")
                md_lines.append(
                    f"- **Выручка**: {forecast['revenue_forecast'][0]:,.2f} "
                    f"({trend_str})"
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
                    md_lines.append(
                        f"- **Качество прогноза (R²)**: {r2:.3f} ({quality})"
                    )
            md_lines.append("")
        else:
            md_lines.append("## Прогноз")
            md_lines.append("")
            md_lines.append(
                f"_{forecast.get('message', 'Прогноз недоступен')}_"
            )
            md_lines.append("")

        md_lines.append("## Визуализации")
        md_lines.append("")

        viz_titles = {
            "distribution": "Распределение сумм транзакций",
            "revenue_by_service": "Выручка по услугам",
            "revenue_by_age": "Зависимость средней суммы от возраста",
            "monthly_trend": "Динамика выручки и транзакций",
            "html_report": "Интерактивный HTML-отчет",
        }

        for viz_name, viz_path in viz_paths.items():
            if viz_name in viz_titles:
                path = (
                    Path(viz_path) if isinstance(viz_path, str) else viz_path
                )
                relative_path = path.relative_to(self.report_dir)
                md_lines.append(f"### {viz_titles[viz_name]}")
                md_lines.append("")
                md_lines.append(f"![]({relative_path})")
                md_lines.append("")

        md_lines.append("---")
        md_lines.append("")
        md_lines.append("## Метаданные")
        md_lines.append("")
        md_lines.append(f"- **ID отчета**: `{self.timestamp}`")
        md_lines.append(
            "- **JSON-данные**: `report_metadata/analysis_results_"
            f"{self.timestamp}.json`"
        )

        md_path = self.report_dir / "REPORT.md"
        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        logger.info(f"Saved Markdown report: {md_path}")
        return md_path

    def _format_timestamp(self) -> str:
        """Format timestamp for human reading."""
        if not self.timestamp:
            return "N/A"
        dt = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
        return dt.strftime("%d.%m.%Y %H:%M:%S")
