"""
Visualization utilities for analysis results.
"""

from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns
from plotly.subplots import make_subplots
from structlog import get_logger

from app.domain.entities import NetWorthLevel

logger = get_logger(__name__)


class VisualizationService:
    """Service for creating data visualizations."""

    def __init__(self, output_dir: Path):
        """
        Initialize visualization service.

        Args:
            output_dir: Directory to save plots.
        """
        self.output_dir = output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        sns.set_style("whitegrid")
        plt.rcParams["figure.figsize"] = (12, 6)

    def plot_transaction_distribution(
        self,
        amounts: list[float],
        filename: str = "transaction_distribution.png",
    ) -> Path:
        """
        Plot distribution of transaction amounts.

        Args:
            amounts: List of transaction amounts.
            filename: Output filename.

        Returns:
            Path to saved plot.
        """
        _, axes = plt.subplots(1, 2, figsize=(15, 5))

        axes[0].hist(amounts, bins=50, edgecolor="black", alpha=0.7)
        axes[0].set_title("Распределение сумм транзакций")
        axes[0].set_xlabel("Сумма")
        axes[0].set_ylabel("Количество транзакций")

        axes[1].boxplot(amounts)
        axes[1].set_title("Ящик с усами (распределение)")
        axes[1].set_ylabel("Сумма")

        plt.tight_layout()

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()

        logger.info(f"Saved distribution plot to {output_path}")
        return output_path

    def plot_revenue_by_service(
        self,
        services: list[dict[str, Any]],
        filename: str = "revenue_by_service.png",
    ) -> Path:
        """
        Plot revenue by service (bar and pie charts).

        Args:
            services: Service performance data.
            filename: Output filename.

        Returns:
            Path to saved plot.
        """
        _, axes = plt.subplots(1, 2, figsize=(15, 6))

        df = pd.DataFrame(services)
        df = df.sort_values("total_revenue", ascending=True)

        try:
            cmap = mpl.colormaps["viridis_r"]
        except KeyError:
            cmap = mpl.colormaps["viridis"]

        colors = [cmap(i / len(df)) for i in range(len(df))]

        bars = axes[0].barh(df["service"], df["total_revenue"], color=colors)
        axes[0].set_title("Выручка по услугам")
        axes[0].set_xlabel("Выручка")

        for bar, revenue in zip(bars, df["total_revenue"], strict=True):
            axes[0].text(
                revenue,
                bar.get_y() + bar.get_height() / 2,
                f" {revenue:,.0f}",
                va="center",
                fontsize=9,
            )

        top_5 = df.nlargest(5, "total_revenue")
        others = df.iloc[5:]

        if not others.empty:
            pie_data = pd.concat([
                top_5,
                pd.DataFrame([
                    {
                        "service": "Остальные",
                        "total_revenue": others["total_revenue"].sum(),
                    }
                ]),
            ])
        else:
            pie_data = top_5

        axes[1].pie(
            pie_data["total_revenue"],
            labels=pie_data["service"],
            autopct="%1.1f%%",
            startangle=90,
        )
        axes[1].set_title("Доля выручки по услугам")

        plt.tight_layout()

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()

        return output_path

    def plot_revenue_by_age(
        self, data: list[dict[str, Any]], filename: str = "revenue_by_age.png"
    ) -> Path:
        """
        Plot average transaction amount by client age.

        Args:
            data: List of dicts with age and avg_amount.
            filename: Output filename.

        Returns:
            Path to saved plot.
        """
        df = pd.DataFrame(data)
        df = df.sort_values("age")

        plt.figure(figsize=(12, 6))

        sns.regplot(
            data=df,
            x="age",
            y="avg_amount",
            scatter_kws={"alpha": 0.5, "s": 50},
            line_kws={"color": "red", "label": "Тренд"},
        )

        plt.title("Зависимость средней суммы транзакции от возраста клиента")
        plt.xlabel("Возраст клиента")
        plt.ylabel("Средняя сумма транзакции")
        plt.grid(True, alpha=0.3)
        plt.legend()

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()

        return output_path

    def plot_monthly_trend(
        self,
        monthly_data: list[dict[str, Any]],
        filename: str = "monthly_trend.png",
    ) -> Path:
        """
        Plot monthly revenue trend.

        Args:
            monthly_data: Monthly revenue data.
            filename: Output filename.

        Returns:
            Path to saved plot.
        """
        df = pd.DataFrame(monthly_data)

        fig, ax1 = plt.subplots(figsize=(12, 6))

        color = "tab:blue"
        ax1.set_xlabel("Месяц")
        ax1.set_ylabel("Выручка", color=color)
        ax1.plot(
            df["period"],
            df["revenue"],
            marker="o",
            color=color,
            linewidth=2,
            label="Выручка",
        )
        ax1.tick_params(axis="y", labelcolor=color)

        ax2 = ax1.twinx()
        color = "tab:orange"
        ax2.set_ylabel("Количество транзакций", color=color)
        ax2.bar(
            df["period"],
            df["transaction_count"],
            alpha=0.3,
            color=color,
            label="Транзакции",
        )
        ax2.tick_params(axis="y", labelcolor=color)

        plt.title("Динамика выручки и количества транзакций")
        fig.autofmt_xdate(rotation=45)
        fig.tight_layout()

        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=100, bbox_inches="tight")
        plt.close()

        return output_path

    def generate_report(
        self,
        transactions: pd.DataFrame,
        clients: pd.DataFrame,
        output_file: str = "analysis_report.html",
    ) -> Path:
        """
        Generate HTML report with all visualizations.

        Args:
            transactions: Transactions DataFrame.
            clients: Clients DataFrame.
            output_file: Output HTML filename.

        Returns:
            Path to saved report.
        """
        clients_with_segments = clients.copy()

        def get_segment(net_worth):
            if pd.isna(net_worth):
                return "Неизвестно"
            return NetWorthLevel.from_amount(net_worth).value

        clients_with_segments["net_worth_level"] = clients_with_segments[
            "net_worth"
        ].apply(get_segment)

        fig = make_subplots(
            rows=2,
            cols=2,
            subplot_titles=(
                "Распределение сумм",
                "Выручка по услугам",
                "Транзакции по городам",
                "Сегменты клиентов",
            ),
            specs=[
                [{"type": "xy"}, {"type": "xy"}],
                [{"type": "xy"}, {"type": "domain"}],
            ],
        )

        fig.add_trace(
            go.Histogram(
                x=transactions["amount"],
                nbinsx=50,
                name="Суммы",
                marker_color="blue",
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

        service_rev = (
            transactions
            .groupby("service_category")["amount"]
            .sum()
            .reset_index()
        )
        service_rev = service_rev.sort_values("amount", ascending=True)

        fig.add_trace(
            go.Bar(
                y=service_rev["service_category"],
                x=service_rev["amount"],
                name="Выручка",
                orientation="h",
                marker_color="green",
                text=service_rev["amount"].apply(lambda x: f"{x:,.0f}"),
                textposition="outside",
            ),
            row=1,
            col=2,
        )

        city_counts = transactions["city"].value_counts().head(10)

        fig.add_trace(
            go.Bar(
                x=city_counts.values,
                y=city_counts.index,
                name="Города",
                orientation="h",
                marker_color="orange",
                text=city_counts.values,
                textposition="outside",
            ),
            row=2,
            col=1,
        )

        segments = clients_with_segments["net_worth_level"].value_counts()

        fig.add_trace(
            go.Pie(
                labels=segments.index,
                values=segments.values,
                name="Сегменты",
                hole=0.3,
                marker={
                    "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
                },
            ),
            row=2,
            col=2,
        )

        fig.update_layout(
            height=800,
            title_text="Финансовый анализ - Отчет",
            showlegend=False,
            template="plotly_white",
        )

        fig.update_xaxes(title_text="Сумма", row=1, col=1)
        fig.update_yaxes(title_text="Частота", row=1, col=1)

        fig.update_xaxes(title_text="Выручка", row=1, col=2)
        fig.update_yaxes(title_text="Услуга", row=1, col=2)

        fig.update_xaxes(title_text="Количество транзакций", row=2, col=1)
        fig.update_yaxes(title_text="Город", row=2, col=1)

        output_path = self.output_dir / output_file
        fig.write_html(str(output_path), include_plotlyjs="cdn")

        logger.info(f"Generated HTML report: {output_path}")
        return output_path
