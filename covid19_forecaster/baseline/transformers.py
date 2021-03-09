import logging

logger = logging.getLogger("fbprophet.plot")
logger.setLevel(logging.CRITICAL)


from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from fbprophet import Prophet
from sklearn.base import TransformerMixin

from .. import io
from ..utils import get_fiscal_year
from .fyp import FY20_BUDGET


@dataclass
class BaselineForecaster(TransformerMixin):
    """
    Transformer to produce a baseline forecast from actuals.
    """

    fit_kwargs: Optional[dict] = field(default_factory=dict)
    fit_start_date: Optional[str] = None
    fit_stop_date: Optional[str] = "2020-03-31"
    forecast_stop_date: Optional[str] = "2022-06-30"

    def fit(self, data):
        """
        Fit the data.

        Notes
        -----
        Data must have a Datetime index.
        """
        # Do some checks
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("Index for input data should be a DatetimeIndex")

        # Set freq
        self.freq_ = data.index.inferred_freq
        if self.freq_ is None:
            raise ValueError("Freq of input datetime index cannot be None")

        return self

    def transform(self, data):
        """
        Run the forecast for each column in data.
        """
        # Trim the fit period
        if self.fit_start_date is not None:
            data = data.loc[self.fit_start_date :]
        if self.fit_stop_date is not None:
            data = data.loc[: self.fit_stop_date]

        # Get the fit kwargs
        fit_kwargs = {
            "daily_seasonality": False,
            "weekly_seasonality": False,
            "n_changepoints": min(int(0.7 * len(data)), 25),
            **self.fit_kwargs,
        }

        # Fit each variable
        out = []
        for col in data.columns:

            # Format data for Prophet
            df = (
                data[col]
                .rename_axis("ds")
                .reset_index()
                .rename(columns={col: "y"})
                .sort_values("ds")
            )

            # Initialize and fit the model
            model = Prophet(**fit_kwargs)
            model.fit(df)

            # Get the forecast period
            periods = (
                pd.to_datetime(self.forecast_stop_date).to_period(
                    self.freq_[0]
                )
                - df["ds"].max().to_period(self.freq_[0])
            ).n
            future = model.make_future_dataframe(
                periods=periods, freq=self.freq_
            )

            # Forecast
            forecast = model.predict(future)

            # Add the yearly term too (in absolute units)
            forecast["yearly"] *= forecast["trend"]

            # Keep total & uncertainty levels
            forecast = (
                forecast[
                    [
                        "ds",
                        "yhat",
                        "yhat_lower",
                        "yhat_upper",
                        "yearly",
                        "trend",
                    ]
                ]
                .rename(
                    columns={
                        "ds": "date",
                        "yhat": "total",
                        "yhat_lower": "lower",
                        "yhat_upper": "upper",
                    }
                )
                .set_index("date")
            )

            # If we're doing this by sector, we need to add another
            # level to the column index
            if len(data.columns) > 1:
                forecast.columns = pd.MultiIndex.from_product(
                    [forecast.columns, [col],]
                )

            # Save
            out.append(forecast)

        return pd.concat(out, axis=1)


@dataclass
class CalibrateToBudget(TransformerMixin):
    """Calibrate revenues to FY20 budget data."""

    tax_name: str

    def __post_init__(self):

        self.rates = None
        try:
            self.rates = io.load_tax_rates(self.tax_name)
        except:
            self.rates = None

    def fit(self, X, y=None):
        """Fit the data."""

        raw_forecast = X.copy()
        raw_forecast.index = pd.Index(
            [get_fiscal_year(dt) for dt in X.index], name="fiscal_year"
        )

        # Rescale by growth rates (if we have them)
        if self.tax_name in FY20_BUDGET.growth_rates:

            # Get tax base growth rates
            growth_rates = self.get_forecasted_growth_rates(raw_forecast)

            # Rescale based on growth
            correction_factors = (
                (1 + FY20_BUDGET.growth_rates[self.tax_name])
                / (1 + growth_rates)
            ).dropna()

        # No rescaling necessary
        else:

            correction_factors = pd.DataFrame(
                {
                    "fiscal_year": [2020, 2021, 2022, 2023, 2024, 2025],
                    "growth_rate": np.ones(6),
                }
            ).set_index("fiscal_year")["growth_rate"]

        # Rescale FY20 by FYP revenue
        fy20_revenue = raw_forecast.loc[2020, "total"].sum()
        if X.columns.nlevels > 1:
            fy20_revenue = fy20_revenue.sum()

        correction_factors.loc[2020] = (
            FY20_BUDGET.revenues[self.tax_name] / fy20_revenue
        )

        # Take cumulative product
        self.correction_factors_ = correction_factors.sort_index().cumprod()

        return self

    def get_forecasted_growth_rates(self, forecast):
        """
        Calculate the tax base growth rates from the forecasted
        revenues.
        Parameters
        ----------
        tax_name : str
            the name of the tax (to load the rates)
        forecast : DataFrame
            the revenue forecast
        """
        X = forecast.copy()["total"]
        N = X.groupby("fiscal_year").sum().sort_index()
        if not isinstance(N, pd.Series):
            N = N.sum(axis=1)
        if self.rates is not None:
            N /= self.rates.loc[N.index, "rate"].values

        return N.diff() / N.shift()

    def transform(self, X):
        """
        Calibrate the revenue forecast to match the projections in
        the forecasted FY21 - FY25 Five Year Plan.
        """

        raw_forecast = X.copy()
        raw_forecast.index = pd.Index(
            [get_fiscal_year(dt) for dt in X.index], name="fiscal_year"
        )

        # Calibrate!
        calibrated = raw_forecast.copy()
        for fy, row in calibrated.iterrows():
            if fy in self.correction_factors_.index:
                row *= self.correction_factors_.loc[fy]

        calibrated.index = X.index
        return calibrated


@dataclass
class RevenueToTaxBase(TransformerMixin):
    """Convert from revenue to tax base."""

    tax_name: str

    def __post_init__(self):

        self.rates = None
        try:
            self.rates = io.load_tax_rates(self.tax_name)
        except:
            self.rates = None

    def fit(self, X, y=None):
        """Fit the data."""
        return self

    def _transform(self, X, inverse=False):
        """Internal function to do transformation."""

        # No transformation needed
        if self.rates is None:
            return X

        # Start from a copy
        fiscal_years = [get_fiscal_year(dt) for dt in X.index]
        out = X.copy()

        # Loop over all of the columns (columns can be a multi-index here)
        for col in out.columns:

            # Get the column and index by the fiscal years
            df = X[col].copy()
            df.index = fiscal_years

            # Do the transformation (pandas will align the indices)
            if not inverse:
                rescaled = (df / self.rates["rate"]).dropna()
            else:
                rescaled = (df * self.rates["rate"]).dropna()

            # Reset the index back to the original
            rescaled.index = X.index

            # And save it
            out[col] = rescaled

        return out

    def transform(self, X):
        """Do the transformation from revenue to tax base."""
        return self._transform(X)

    def inverse_transform(self, X):
        """Do the inverse transformation from revenue to tax base."""
        return self._transform(X, inverse=True)


@dataclass
class DisaggregateCollectionsBySector:
    """
    Given monthly total collections, disaggregate by industry, using
    historical data for collections by industry.
    """

    sector_data: pd.DataFrame

    def fit_transform(self, data, **kwargs):
        """Convenience function"""

        # Fit
        self.fit(data, **kwargs)

        # Transform
        return self.transform(data, **kwargs)

    def fit(self, data, key="sector"):
        """Fit the data."""

        # Check columns exist
        for col in ["fiscal_year", key]:
            if col not in self.sector_data.columns:
                raise ValueError(
                    f"Missing column '{col}' in input sector data"
                )

        # Determine how to group
        self.time_cols_ = ["fiscal_year"]
        if "month" in self.sector_data.columns:
            self.time_cols_ += ["month"]

    def transform(self, data, key="sector"):
        """
        Transform the input data to disaggregate by industry.

        Note: if historical data by industry is not available
        for a specific month, the most recent observation is used.
        """
        # Aggregate over sector to get total for each time bin
        sector_agg = self.sector_data.groupby(self.time_cols_)["total"].sum()

        # Get the sector shares
        # This is the share of collections to a specific sector per a given time period
        # e.g., month or fiscal year
        sector_shares = (
            self.sector_data.groupby(self.time_cols_ + [key])["total"].sum()
            / sector_agg
        ).rename("sector_share")

        # Check if the time periods for the input data and historical data are misaligned
        i = data.set_index(self.time_cols_).index
        missing = i.difference(sector_agg.index)

        # Impute missing industry shares using most recent observations
        if len(missing):

            # Setup
            existing_index = sector_shares.index
            unique_sectors = existing_index.get_level_values(level=-1).unique()

            # New time periods that we need to add to historical data
            new_index = []
            for ii in missing:
                if not isinstance(ii, tuple):
                    ii = (ii,)
                new_index += [(*ii, sector) for sector in unique_sectors]

            # Reindex and impute missing with most recent obs
            sector_shares = (
                sector_shares.reindex(existing_index.tolist() + new_index)
                .sort_index(level=-1, sort_remaining=True)
                .fillna(method="ffill")
            )

        out = (
            data.merge(
                sector_shares.reset_index(), on=self.time_cols_, how="left"
            )
            .assign(total=lambda df: df["total"] * df["sector_share"])
            .drop(labels=["sector_share"], axis=1)
        )
        return out
