"""
Forecasting module for predicting future demand.

Uses simple linear regression for trend analysis.
"""

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from structlog import get_logger

logger = get_logger(__name__)


class DemandForecast:
    """
    Forecast demand using linear regression.

    Predicts future transaction counts and revenue based on historical trends.
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize forecast model.

        Args:
            confidence_level: Confidence level for prediction intervals
        """
        self.confidence_level = confidence_level
        self.model_counts: LinearRegression | None = None
        self.model_revenue: LinearRegression | None = None
        self.history: pd.DataFrame | None = None

    def fit(
        self,
        dates: list[datetime],
        counts: list[int],
        revenues: list[float],
    ) -> "DemandForecast":
        """
        Fit regression models to historical data.

        Args:
            dates: List of dates
            counts: Transaction counts per period
            revenues: Total revenue per period

        Returns:
            Self for method chaining
        """
        df = pd.DataFrame({
            "date": dates,
            "count": counts,
            "revenue": revenues,
        })
        df = df.sort_values("date")

        df["days"] = (df["date"] - df["date"].min()).dt.days

        days_array = df["days"].to_numpy().reshape(-1, 1)
        X: NDArray[np.float64] = days_array.astype(np.float64)

        self.history = df

        if len(counts) >= 2:
            self.model_counts = LinearRegression()
            y_counts_array = df["count"].to_numpy()
            y_counts: NDArray[np.float64] = y_counts_array.astype(np.float64)
            self.model_counts.fit(X, y_counts)

        if len(revenues) >= 2:
            self.model_revenue = LinearRegression()
            y_revenues_array = df["revenue"].to_numpy()
            y_revenues: NDArray[np.float64] = y_revenues_array.astype(
                np.float64
            )
            self.model_revenue.fit(X, y_revenues)

        logger.info(
            "Forecast models fitted",
            data_points=len(df),
            count_model=self.model_counts is not None,
            revenue_model=self.model_revenue is not None,
        )

        return self

    def predict(
        self, periods: int = 1, period_days: int = 30
    ) -> dict[str, Any]:
        """
        Predict future demand.

        Args:
            periods: Number of periods to forecast
            period_days: Days per period

        Returns:
            Dictionary with forecast results
        """
        if self.history is None:
            raise ValueError("Model must be fitted before prediction")

        if self.model_counts is None and self.model_revenue is None:
            return {"error": "No models available for prediction"}

        last_date = self.history["date"].max()
        future_dates = [
            last_date + timedelta(days=(i + 1) * period_days)
            for i in range(periods)
        ]

        first_date = self.history["date"].min()
        future_days_raw = np.array(
            [(d - first_date).days for d in future_dates],
            dtype=np.float64,
        )
        future_days_np: NDArray[np.float64] = future_days_raw.reshape(-1, 1)

        result: dict[str, Any] = {
            "forecast_periods": periods,
            "period_days": period_days,
            "forecast_dates": [d.isoformat() for d in future_dates],
            "count_forecast": [],
            "revenue_forecast": [],
            "metrics": {},
        }

        if self.model_counts is not None:
            count_pred = self.model_counts.predict(future_days_np)
            count_pred = np.maximum(count_pred, 0)
            result["count_forecast"] = [round(float(c)) for c in count_pred]

            X_hist_raw = self.history["days"].to_numpy().reshape(-1, 1)
            X_hist: NDArray[np.float64] = X_hist_raw.astype(np.float64)
            y_hist_raw = self.history["count"].to_numpy()
            y_hist: NDArray[np.float64] = y_hist_raw.astype(np.float64)
            y_pred = self.model_counts.predict(X_hist)

            result["metrics"]["count_mae"] = float(
                mean_absolute_error(y_hist, y_pred)
            )
            result["metrics"]["count_r2"] = float(r2_score(y_hist, y_pred))

            coef = float(self.model_counts.coef_[0])
            result["count_trend"] = (
                "increasing"
                if coef > 0
                else "decreasing"
                if coef < 0
                else "stable"
            )

        if self.model_revenue is not None:
            revenue_pred = self.model_revenue.predict(future_days_np)
            revenue_pred = np.maximum(revenue_pred, 0)
            result["revenue_forecast"] = [
                round(float(r), 2) for r in revenue_pred
            ]

            X_hist_rev_raw = self.history["days"].to_numpy().reshape(-1, 1)
            X_hist_rev: NDArray[np.float64] = X_hist_rev_raw.astype(np.float64)
            y_hist_rev_raw = self.history["revenue"].to_numpy()
            y_hist_rev: NDArray[np.float64] = y_hist_rev_raw.astype(np.float64)
            y_pred = self.model_revenue.predict(X_hist_rev)

            result["metrics"]["revenue_mae"] = float(
                mean_absolute_error(y_hist_rev, y_pred)
            )
            result["metrics"]["revenue_r2"] = float(
                r2_score(y_hist_rev, y_pred)
            )

            coef = float(self.model_revenue.coef_[0])
            result["revenue_trend"] = (
                "increasing"
                if coef > 0
                else "decreasing"
                if coef < 0
                else "stable"
            )

        return result


def get_seasonality(self) -> dict[str, float]:
    """
    Detect simple seasonality patterns.

    Returns:
        Dictionary with seasonality metrics
    """
    if self.history is None or len(self.history) < 12:
        return {}

    hist = self.history.copy()
    hist = hist.set_index("date")

    monthly_avg = hist["count"].resample("ME").mean()

    result: dict[str, float] = {}
    for date, avg in monthly_avg.items():
        month_num = date.month
        month_key = f"month_{month_num:02d}"
        result[month_key] = float(avg)

    return result


def create_demand_forecast(
    monthly_data: list[dict[str, Any]],
    forecast_months: int = 1,
    min_months: int = 3,
) -> dict[str, Any]:
    """
    Create demand forecast from monthly data.

    Args:
        monthly_data: List of monthly data with 'period' and
            'transaction_count'
        forecast_months: Number of months to forecast
        min_months: Minimum months required for forecast

    Returns:
        Forecast results
    """
    if len(monthly_data) < min_months:
        return {
            "available": False,
            "message": f"Insufficient data: need {min_months} months, "
            f"have {len(monthly_data)}",
        }

    dates: list[datetime] = []
    counts: list[int] = []
    revenues: list[float] = []

    for item in monthly_data:
        year_str, month_str = item["period"].split("-")
        year = int(year_str)
        month = int(month_str)

        date = datetime(year, month, 1)
        dates.append(date)

        counts.append(int(item["transaction_count"]))
        revenues.append(float(item["revenue"]))

    forecast = DemandForecast()
    forecast.fit(dates, counts, revenues)

    result = forecast.predict(periods=forecast_months, period_days=30)
    result["available"] = True
    result["historical_data"] = {
        "dates": [d.isoformat() for d in dates],
        "counts": counts,
        "revenues": revenues,
    }

    return result
