from .fyp import FY20_REVENUES, FYP_GROWTH_RATES
from .core import (
    load_historical_collections,
    project_tax_revenue,
    calibrate_forecast,
)
from phila_style.matplotlib import get_theme
from phila_style import get_digital_standards
from matplotlib import pyplot as plt
import pickle
from pathlib import Path


def _get_monthly_total(df):
    return df.groupby("date")["total"].sum().sort_index()


class BaselineForecast(object):
    """
    A baseline revenue forecast, calibrated to the
    fiscal year totals presented in the proposed FY21-FY25
    Five Year Plan.

    Parameters
    ----------
    tax_name : str
        the name of the tax to project
    seasonality_mode : str
        either "multiplicative" or "additive"
    """

    def __init__(self, tax_name, seasonality_mode="multiplicative"):

        # Store the tax name
        if tax_name not in FY20_REVENUES:
            raise ValueError(
                f"allowed values for 'tax_name' are: {list(FY20_REVENUES)}"
            )
        self.tax_name = tax_name

        # Format the historical data
        self.historical = load_historical_collections(tax_name)

        # Get the raw forecast
        self.raw_forecast = project_tax_revenue(
            tax_name, self.historical, seasonality_mode=seasonality_mode
        )

        # Readjust for sales
        if tax_name == "sales":

            # Subtract from forecast
            valid = self.raw_forecast["fiscal_year"] >= 2015
            for col in ["total", "lower", "upper"]:
                self.raw_forecast.loc[valid, col] -= (
                    120e6 / 12 / self.raw_forecast["naics_sector"].nunique()
                )

            # Subtract from historical
            valid = self.historical["fiscal_year"] >= 2015
            self.historical.loc[valid, "total"] -= (
                120e6 / 12 / self.historical["naics_sector"].nunique()
            )

        # The calibrated forecast
        self.forecast = calibrate_forecast(tax_name, self.raw_forecast)

    @property
    def mean_abs_error(self):
        """The mean absolute error of the fit"""
        P = _get_monthly_total(self.raw_forecast)
        H = _get_monthly_total(self.historical)

        return (H - P).dropna().abs().mean()

    @property
    def mean_abs_percent_error(self):
        """Mean absolute percent error of the fit"""
        P = _get_monthly_total(self.raw_forecast)
        H = _get_monthly_total(self.historical)

        return ((H - P) / H).dropna().abs().mean()

    @property
    def mean_rms(self):
        """The average root mean squared error of the fit"""
        P = _get_monthly_total(self.raw_forecast)
        H = _get_monthly_total(self.historical)

        return ((H - P) ** 2).dropna().mean() ** 0.5

    def plot(self, kind="raw"):
        """
        Plot the forecast, including uncertainty, as well as
        the historical data points.

        Parameters
        ----------
        kind : str
            which forecast to plot; either 'raw' or 'calibrated'
        """

        # Check inputs
        assert kind in ["raw", "calibrated"]

        # Load the palettes
        palette = get_digital_standards()

        with plt.style.context(get_theme()):

            fig, ax = plt.subplots(
                figsize=(6, 4), gridspec_kw=dict(left=0.15, bottom=0.1)
            )

            # Plot the prediction
            if kind == "raw":
                df = self.raw_forecast
            else:
                df = self.forecast
            P = df.groupby("date")[["total", "lower", "upper"]].sum()
            P.plot(
                lw=1,
                ax=ax,
                y="total",
                color=palette["dark-ben-franklin"],
                zorder=10,
                legend=False,
            )

            # Uncertainty
            ax.fill_between(
                P.index,
                P["lower"],
                P["upper"],
                facecolor=palette["dark-ben-franklin"],
                alpha=0.7,
                zorder=9,
            )

            # Plot the historical scatter
            H = self.historical.groupby("date")["total"].sum()
            H.reset_index().plot(
                kind="scatter",
                x="date",
                y="total",
                ax=ax,
                color=palette["love-park-red"],
                zorder=11,
            )

            # Format
            ax.set_yticklabels([f"${x/1e6:.1f}M" for x in ax.get_yticks()])
            ax.set_xlabel("")
            ax.set_ylabel("")

            return fig, ax

    def save(self, filename):
        pickle.dump(self, Path(filename).open("wb"))

    @staticmethod
    def load(filename):
        return pickle.load(Path(filename).open("rb"))
