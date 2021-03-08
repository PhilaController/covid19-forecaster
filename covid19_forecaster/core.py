from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from phila_style import get_digital_standards
from phila_style.matplotlib import get_theme

from .baseline.core import BaselineForecast


@dataclass
class RevenueForecast(ABC):
    """
    A revenue forecast. This class is the base class for
    forecasts for individual taxes.

    The forecast is composed of:
        - A smooth, pre-COVID baseline forecast that captures
        seasonality (computed using Prophet)
        - A post-COVID forecast parameterized as a decline
        from this baseline.

    Parameters
    ----------
    tax_name : str
        the name of the tax to forecast
    forecast_start :
        the start date for the predicted forecast
    forecast_stop :
        the stop date for the predicted forecast
    freq : {'M', 'Q'}
        the frequency of the forecast, either monthly or quarterly
    ignore_sectors :
        whether to include sectors in the forecast
    use_subsectors :
        whether to include subsectors when forecasting
    fresh :
        if True, calculate a fresh baseline fit
    fit_kwargs :
        additional parameters to pass
    """

    tax_name: str
    forecast_start: str
    forecast_stop: str
    freq: str
    baseline_start: str = "2014-07-01"
    baseline_stop: str = "2020-03-31"
    ignore_sectors: Optional[bool] = False
    use_subsectors: Optional[bool] = False
    sector_crosswalk: Optional[dict] = None
    fresh: Optional[bool] = False
    fit_kwargs: Optional[dict] = field(default_factory=dict)
    agg_after_fitting: Optional[bool] = False
    flat_growth: Optional[bool] = False

    def __post_init__(self):

        # Initialize the baseline forecast
        self.baseline = BaselineForecast(
            tax_name=self.tax_name,
            freq=self.freq,
            fit_start_date=self.baseline_start,
            fit_stop_date=self.baseline_stop,
            ignore_sectors=self.ignore_sectors,
            use_subsectors=self.use_subsectors,
            fresh=self.fresh,
            fit_kwargs=self.fit_kwargs,
            sector_crosswalk=self.sector_crosswalk,
            agg_after_fitting=self.agg_after_fitting,
            flat_growth=self.flat_growth,
        )

        # Create forecast dates index
        freq = self.baseline.inferred_freq
        self.forecast_dates = pd.date_range(
            self.forecast_start, self.forecast_stop, freq=freq
        )

    def __repr__(self):

        name = self.__class__.__name__
        return (
            f"{name}(tax_name='{self.tax_name}', "
            f"forecast_start='{self.forecast_start}', "
            f"forecast_stop='{self.forecast_stop}')"
        )

    @property
    def actuals_raw(self):
        """The actual revenue collection data."""
        return self.baseline.actuals_raw

    @property
    def has_sectors(self):
        """Whether the forecast uses sector-based data."""
        return self.baseline.has_sectors

    @property
    def total_baseline(self):
        """The total baseline, summed over any sectors."""

        baseline = self.baseline.forecasted_total_revenue_
        return baseline.loc[: self.forecast_stop]

    @property
    def total_forecast(self):
        """The total forecast, summed over any sectors"""

        assert hasattr(self, "forecast_"), "Please call run_forecast() first"

        forecast = self.forecast_
        if self.has_sectors:
            forecast = forecast.sum(axis=1)

        return forecast.loc[: self.forecast_stop]

    @property
    def total_actuals(self):
        """The total actuals"""
        return self.baseline.actual_total_revenue_

    @property
    def actuals(self):
        """The actuals"""
        actuals = self.baseline.actual_revenue_.squeeze()
        return actuals

    @property
    def baseline_(self):
        """The baseline"""
        baseline = self.baseline.forecasted_revenue_["total"]
        return baseline.loc[: self.forecast_stop]

    def run_forecast(self, scenario):
        """Run the forecast for the specified scenario."""
        # ---------------------------------------------------------------------
        # STEP 1: Start from the baseline forecast over the forecast period
        # ---------------------------------------------------------------------
        start = self.forecast_start
        stop = self.forecast_stop
        self.forecast_ = self.baseline.forecasted_revenue_["total"].copy()
        self.forecast_ = self.forecast_.loc[:stop]

        # ---------------------------------------------------------------------
        # STEP 2: Iterate over each time step and apply the reduction
        # ---------------------------------------------------------------------
        for date in self.forecast_.loc[start:stop].index:

            # This is the baseline
            baseline = self.forecast_.loc[date]

            # Get the forecasted change
            self.forecast_.loc[date] = self.get_forecasted_decline(
                date, baseline, scenario=scenario
            )

        return self.forecast_

    @abstractmethod
    def get_forecasted_decline(self, date, baseline, scenario):
        """
        For a given scenario, return the revenue
        decline from the baseline forecast for the specific date.
        """
        pass

    def plot(self, normalized=False, month_to_quarters=False):
        """
        Plot the baseline and scenario forecasts, as well as the
        historical data points.
        """

        def to_quarters(df):
            if not month_to_quarters:
                return df
            else:
                return df.groupby(pd.Grouper(freq="QS")).sum()

        baseline = to_quarters(self.total_baseline)
        forecast = to_quarters(self.total_forecast)
        actuals = to_quarters(self.total_actuals)

        # Load the palettes
        palette = get_digital_standards()

        with plt.style.context(get_theme()):

            fig, ax = plt.subplots(
                figsize=(6, 4), gridspec_kw=dict(left=0.15, bottom=0.1)
            )

            # Not normalized
            if not normalized:
                baseline.plot(
                    lw=1,
                    ax=ax,
                    y="total",
                    color=palette["medium-gray"],
                    zorder=10,
                    legend=False,
                    label="Baseline",
                )

                # Get the forecast, with one point previous to where it started
                i = forecast.index.get_loc(
                    self.forecast_start, method="nearest"
                )
                forecast = forecast.iloc[i:]

                # Plot the forecast
                forecast.plot(
                    lw=1,
                    ax=ax,
                    y="total",
                    color=palette["ben-franklin-blue"],
                    zorder=10,
                    legend=False,
                    label="Forecast",
                )

                # Plot the actuals scatter
                actuals.reset_index(name="total").plot(
                    kind="scatter",
                    x="date",
                    y="total",
                    ax=ax,
                    color=palette["love-park-red"],
                    zorder=11,
                    label="Actuals",
                )

            else:

                # Plot the forecast
                N = forecast / baseline
                N.plot(
                    lw=1,
                    ax=ax,
                    y="total",
                    color=palette["ben-franklin-blue"],
                    zorder=10,
                    legend=False,
                    label="Forecast",
                )

                # Plot the actuals scatter
                A = (actuals / baseline).dropna()
                A.reset_index(name="total").plot(
                    kind="scatter",
                    x="date",
                    y="total",
                    ax=ax,
                    color=palette["love-park-red"],
                    zorder=11,
                    label="Actuals",
                )

            # Format
            ax.set_yticks(ax.get_yticks())
            if not normalized:
                ax.set_yticklabels([f"${x/1e6:.0f}M" for x in ax.get_yticks()])
            else:
                ax.set_yticklabels([f"{x*100:.0f}%" for x in ax.get_yticks()])
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.legend(loc=0, fontsize=10)

            return fig, ax

    def summarize(self, include_sectors=False):
        """Summarize."""

        out = []
        labels = ["baseline", "actual", "forecast"]
        for i, df in enumerate([self.baseline_, self.actuals, self.forecast_]):

            if not self.has_sectors:
                df = df.to_frame(name="Total")

            B = df.T.copy()

            if self.has_sectors:
                B.loc["Total"] = B.sum(axis=0)
            B.index = pd.MultiIndex.from_product([[labels[i]], B.index])

            out.append(B)

        X = pd.concat(out, axis=0).swaplevel()
        if self.has_sectors:
            cols = self.actuals.columns.tolist() + ["Total"]
            X = X.loc[cols]
        #
        if not include_sectors:
            X = X.loc[["Total"]]

        return X


class ScenarioForecast:
    """A collection of revenue forecasts for a specific scenario."""

    def __init__(self, *forecasts: RevenueForecast):
        self.forecasts = {f.tax_name: f for f in forecasts}

    @property
    def taxes(self):
        """The names of the taxes in the forecast."""
        return sorted(self.forecasts.keys())

    def __getitem__(self, name):
        """Return a specific forecast."""
        if name in self.taxes:
            return self.forecasts[name]
        return super().__getitem__(name)

    def __getattr__(self, name):
        if name in self.taxes:
            return self.forecasts[name]
        raise AttributeError(f"No such attribute '{name}'")

    def __iter__(self):
        yield from self.taxes

    def summarize(self, include_sectors=False):
        """
        Summarize the scenario by providing actual, baseline,
        and forecast values for each tax.
        """

        out = []
        for tax_name in self:

            # Get the tax name
            tax = self[tax_name]

            # Summarize it
            summary = tax.summarize(include_sectors=include_sectors)
            if not include_sectors:

                # Rename to include tax
                summary = summary.loc[["Total"]].rename(
                    index={"Total": tax.tax_name}, level=0
                )
                summary = summary.rename_axis(("tax", "kind"))

            else:
                summary = pd.concat({tax.tax_name: summary}, names=["tax"])
                summary = summary.rename_axis(("tax", "sector", "kind"))

            out.append(summary)

        # Combine and do the transpose
        # Date is now on column axis with taxes on row axis
        out = pd.concat(out, axis=0)

        # Add a "total" column
        for col in ["actual", "baseline", "forecast"]:
            subset = out.xs(col, axis=0, level=-1)

            total = subset.sum()
            if include_sectors:
                out.loc[("total", "Total", col), :] = total.replace(0, np.nan)
            else:
                out.loc[("total", col), :] = total.replace(0, np.nan)

        return out


@dataclass
class ScenarioComparison:
    """A class to facilitate comparisons of multiple scenario forecasts."""

    scenarios: Dict[str, ScenarioForecast]

    def __repr__(self):
        name = self.__class__.__name__
        return f"{name}(scenarios={self.scenario_names})"

    @property
    def scenario_names(self):
        """The names of the scenarios to compare."""
        return sorted(self.scenarios.keys())

    def __getitem__(self, name):
        """Return a specific scenario."""
        if name in self.scenario_names:
            return self.scenarios[name]
        return super().__getitem__(name)

    def __getattr__(self, name):
        if name in self.scenario_names:
            return self.scenarios[name]
        raise AttributeError(f"No such attribute '{name}'")

    def save(self, path, start_date="2020"):
        """Save the data to an excel file."""

        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:

            # Save the raw scenario data
            for name in self.scenarios:

                # Get the tidy data
                tidy_data = self.get_tidy_data(name)

                # Save it
                sheet_name = f"{name.capitalize()} Data"
                tidy_data.to_excel(writer, sheet_name=sheet_name)

                # The functions to run
                funcs = [
                    self.get_scenario_comparison,
                    self.get_normalized_comparison,
                    self.get_cumulative_diffs,
                ]

                sheets = [
                    "Comparison",
                    "Norm. Comparison",
                    "Total Shortfalls",
                ]
                for f, sheet in zip(funcs, sheets):

                    # Get the result
                    df = f(start_date=start_date)

                    freq = df.columns.inferred_freq
                    if freq[0] == "M":
                        suffix = " (Monthly)"
                    else:
                        suffix = " (Quarterly)"

                    # Save
                    df.to_excel(
                        writer, sheet_name=sheet + suffix, merge_cells=False
                    )

                    # Do quarterly too
                    if freq[0] == "M":
                        df = f(start_date=start_date, quarterly=True)
                        df.to_excel(
                            writer,
                            sheet_name=sheet + " (Quarterly)",
                            merge_cells=False,
                        )

    def get_tidy_data(self, scenario):
        """Raw data in tidy format."""

        # Summarize the scenario
        df = self.scenarios[scenario].summarize()

        # Melt and return
        return (
            df.melt(ignore_index=False, value_name="total")
            .reset_index()
            .sort_values(["date", "tax"])
        )

    def _get_scenario_report(self, func, start_date="2020", quarterly=False):
        """Internal function to get scenario report."""

        out = []
        for i, name in enumerate(self.scenario_names):

            # Summarize the scenario
            df = self.scenarios[name].summarize()

            # Transpose so date is along index
            df = df.T

            # Trim by date
            df = df.loc[start_date:]

            # Check freq
            freq = df.index.inferred_freq

            if freq[0] != "Q" and quarterly:
                grouped = df.T.groupby(pd.Grouper(freq="QS"))
                sel = grouped.size() != 3

                # Sum and set nans
                df = grouped.sum()
                df.loc[sel] = np.nan

            # Save
            out += func(i, df.T, name)

        # Combine
        out = pd.concat(out, axis=0).sort_index()

        # Return with "total" last
        i = out.index.get_level_values(0).unique()
        return out.loc[i.drop("total").tolist() + ["total"]]

    def get_scenario_comparison(self, start_date="2020", quarterly=False):
        """Return forecasts."""

        def report(i, df, name):

            # Drop baseline and actual if not first
            if i == 0:
                df = df.drop("baseline", axis=0, level=1)
            else:
                df = df.drop(["baseline", "actual"], axis=0, level=1)

            # Rename it and save
            return [df.rename(index={"forecast": name})]

        return self._get_scenario_report(
            report, start_date=start_date, quarterly=quarterly
        )

    def get_cumulative_diffs(self, start_date="2020", quarterly=False):
        """Return cumulative differences."""

        def report(i, df, name):

            # initialize output
            out = []

            # Get forecast and baseline
            actuals = df.xs("actual", axis=0, level=1)
            forecast = df.xs("forecast", axis=0, level=1)
            baseline = df.xs("baseline", axis=0, level=1)

            # Do the cumulative diff b/w forecast and baseline
            x = (forecast - baseline).cumsum(axis=1)
            x.index = pd.MultiIndex.from_product([x.index, [name]])
            out.append(x)

            # Add the diff b/w actuals and baseline
            if i == 0:
                x = (actuals.dropna(how="any", axis=1) - baseline).cumsum(
                    axis=1
                )
                x.index = pd.MultiIndex.from_product([x.index, ["actual"]])
                out.append(x)

            return out

        return self._get_scenario_report(
            report, start_date=start_date, quarterly=quarterly
        )

    def get_normalized_comparison(self, start_date="2020", quarterly=False):
        """Return cumulative differences."""

        def report(i, df, name):

            # Baseline
            baseline = df.xs("baseline", axis=0, level=1)

            # Divide by the baseline
            df = df.divide(baseline, axis=0, level=0).drop(
                "baseline", level=1, axis=0
            )

            # Drop actuals
            if i > 0:
                df = df.drop(["actual"], axis=0, level=1)

            # Rename it and save
            return [df.rename(index={"forecast": name})]

        return self._get_scenario_report(
            report, start_date=start_date, quarterly=quarterly
        )
