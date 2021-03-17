from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Union

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

    1. A smooth, pre-COVID baseline forecast that captures
    seasonality (computed using Prophet)
    2. A post-COVID forecast parameterized as a function of the
    baseline; in the simplest case, this forecast is a decline
    from the baseline.

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
    baseline_start : optional
        the start date to fit the baseline
    baseline_stop : optional
        the stop date to fit the baseline; default is just before COVID pandemic
    ignore_sectors : optional
        whether to include sectors in the forecast
    use_subsectors : optional
        whether to include subsectors when forecasting
    sector_crosswalk : optional
        a cross walk to re-align sectors
    fresh : optional
        if True, calculate a fresh baseline fit
    fit_kwargs : optional
        additional parameters to pass
    agg_after_fitting : optional
        whether to aggregate to the desired frequency before or
        after fitting the baseline
    flat_growth : optional
        whether to assume a flat baseline forecast beyond the baseline
        fitting period
    city_sales_only : optional
        whether to transform sales tax data to model only City revenue
    """

    tax_name: str
    forecast_start: str
    forecast_stop: str
    freq: str
    baseline_start: str = "2013-07-01"
    baseline_stop: str = "2020-03-31"
    ignore_sectors: Optional[bool] = False
    use_subsectors: Optional[bool] = False
    sector_crosswalk: Optional[dict] = None
    fresh: Optional[bool] = False
    fit_kwargs: Optional[dict] = field(default_factory=dict)
    agg_after_fitting: Optional[bool] = False
    flat_growth: Optional[bool] = False
    city_sales_only: Optional[bool] = False

    def __post_init__(self):

        # Initialize the baseline forecaster
        self.baseline_forecast = BaselineForecast(
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
            city_sales_only=self.city_sales_only,
        )

        # Create forecast dates index
        freq = self.baseline_forecast.inferred_freq
        self.forecast_dates = pd.date_range(
            self.forecast_start, self.forecast_stop, freq=freq
        )

    def __repr__(self):
        """Improved representation."""

        name = self.__class__.__name__
        return (
            f"{name}(tax_name='{self.tax_name}', "
            f"forecast_start='{self.forecast_start}', "
            f"forecast_stop='{self.forecast_stop}')"
        )

    @property
    def has_sectors(self) -> bool:
        """Whether the forecast uses sector-based data."""
        return self.baseline_forecast.has_sectors

    @property
    def actuals_raw(self) -> pd.DataFrame:
        """
        The  actual revenue collection (raw) data.

        Note: this is in tidy format.
        """
        return self.baseline_forecast.actuals_raw

    @property
    def total_baseline(self) -> pd.Series:
        """
        The total baseline, summed over any sectors.

        Note: This is a pandas Series indexed by date.
        """
        baseline = self.baseline_forecast.forecasted_total_revenue_
        return baseline.loc[: self.forecast_stop]

    @property
    def total_forecast(self) -> pd.Series:
        """
        The total forecast, summed over any sectors. For dates prior
        to the forecast period, the forecast is equal to the baseline.

        Note: This is a pandas Series indexed by date.
        """
        assert hasattr(self, "forecast_"), "Please call run_forecast() first"

        forecast = self.forecast_
        if self.has_sectors:
            forecast = forecast.sum(axis=1)

        return forecast.loc[: self.forecast_stop]

    @property
    def total_actuals(self) -> pd.Series:
        """
        The total actuals, summed over any sectors.

        Note: This is a pandas Series indexed by date.
        """
        return self.baseline_forecast.actual_total_revenue_

    @property
    def actuals(self) -> pd.DataFrame:
        """
        The actuals revenue collections.

        Note: Columns are sectors (if using) or a single column 'Total'
        """
        actuals = self.baseline_forecast.actual_revenue_
        if not self.has_sectors:
            actuals = actuals.rename(columns={"total": "Total"})

        return actuals

    @property
    def baseline(self) -> pd.DataFrame:
        """
        The baseline forecast.

        Note: Columns are sectors (if using) or a single column 'Total'
        """
        # Get the baseline revenue forecast
        baseline = self.baseline_forecast.forecasted_revenue_["total"]
        baseline = baseline.loc[: self.forecast_stop]

        if not self.has_sectors:
            baseline = baseline.to_frame(name="Total")

        return baseline

    def run_forecast(self, scenario: str) -> pd.DataFrame:
        """
        Run the forecast for the specified scenario.

        Note: this must be called before the "forecast_" attribute is calculated.

        Parameters
        ----------
        scenario :
            the name of the scenario to run

        Returns
        -------
        forecast_ :
            the predicted revenue forecast
        """
        # Set up the forecast period
        start = self.forecast_start
        stop = self.forecast_stop

        # ---------------------------------------------------------------------
        # STEP 1: Start from the baseline forecast over the forecast period
        # ---------------------------------------------------------------------
        self.forecast_ = self.baseline.copy()

        # ---------------------------------------------------------------------
        # STEP 2: Iterate over each time step and apply the reduction
        # ---------------------------------------------------------------------
        for date in self.forecast_.loc[start:stop].index:

            # This is the baseline
            # Either a value or a Series for each sector
            baseline = self.baseline.loc[date].squeeze()

            # Get the forecasted change
            forecast_value = self.get_forecast_value(
                date, baseline, scenario=scenario
            )

            # Save
            self.forecast_.loc[date, :] = forecast_value

        # Return the forecast
        return self.forecast_

    @abstractmethod
    def get_forecast_value(
        self,
        date: pd.Timestamp,
        baseline: Union[float, pd.Series],
        scenario: str,
    ) -> Union[float, pd.Series]:
        """
        For a given scenario, return the revenue forecast for the
        specific date and the specific scenario.

        Note: this is abstract — subclasses must define this function!

        Parameters
        ----------
        date :
            the date for the forecast
        baseline :
            the baseline forecast for the specified date
        scenario :
            the scenario to forecast
        """
        pass

    def get_summary(
        self,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Summarize the current forecast, returning the actuals,
        forecast, and baseline.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by sector and kind, where kind includes
            "actual", "forecast" and "baseline". Columns are dates.
        """
        assert hasattr(self, "forecast_"), "Please call run_forecast() first"

        out = []
        labels = ["baseline", "actual", "forecast"]
        for i, df in enumerate([self.baseline, self.actuals, self.forecast_]):

            # Get the data frame with date along column axis
            B = df.T.copy()

            # Add a "Total" row
            if self.has_sectors:
                B.loc["Total"] = B.sum(axis=0)

            # Prepend a level to the index
            B = pd.concat({labels[i]: B}, names=["sector"])
            out.append(B)

        # Combine and make sure index is (tax, kind)
        X = pd.concat(out, axis=0).swaplevel()

        # Re-order the tax indices
        if self.has_sectors:
            cols = self.actuals.columns.tolist() + ["Total"]
            X = X.loc[cols]

        # Just return the "Total"
        if not include_sectors:
            X = X.loc[["Total"]]

        # Summarize to quarters?
        if self.freq == "M" and quarterly:

            # Put date on row axis
            X = X.T

            # Set sum to Nan if not 3 months per quarter
            X = X.groupby(pd.Grouper(freq="QS")).sum(min_count=3)

            # Date on column axis
            X = X.T

        # Trim by start date
        if start_date is not None:
            X = X.T.loc[start_date:].T

        return X.rename_axis(("sector", "kind"))

    def get_normalized_summary(
        self, include_sectors=False, quarterly=False, start_date=None
    ) -> pd.DataFrame:
        """
        Return the actuals & forecast normalized by the baseline.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by sector and kind, where kind includes
            "actual" and "forecast". Columns are dates.
        """
        # Get the summary
        S = self.get_summary(
            include_sectors=include_sectors,
            quarterly=quarterly,
            start_date=start_date,
        )

        # Get the baseline
        baseline = S.xs("baseline", axis=0, level=-1)

        # Create a copy to return and remove baseline
        out = S.copy().drop("baseline", level=-1)
        for name in ["forecast", "actual"]:

            # Normalize the actuals/forecast
            F = S.xs(name, axis=0, level=-1)
            F = F / baseline

            # Set it!
            out.loc[pd.IndexSlice[:, name], :] = F.values

        return out

    def get_baseline_differences(
        self,
        cumulative: bool = True,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return the differences between the baseline and actuals/forecast.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        cumulative :
            whether to return cumulative difference since the specified start date
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by sector and kind, where kind includes
            "actual" and "forecast". Columns are dates.
        """
        # Get the summary
        S = self.get_summary(
            include_sectors=include_sectors,
            quarterly=quarterly,
            start_date=start_date,
        )

        # Get the baseline
        baseline = S.xs("baseline", axis=0, level=-1)

        # Create a copy to return and remove baseline
        out = S.copy().drop("baseline", level=-1)
        for name in ["forecast", "actual"]:

            # Get the differences
            F = S.xs(name, axis=0, level=-1)
            F = F - baseline
            if cumulative:
                F = F.cumsum(axis=1)

            # Set it!
            out.loc[pd.IndexSlice[:, name], :] = F.values

        return out

    def plot(self, normalized=False, month_to_quarters=False, start_date=None):
        """
        Plot the baseline and scenario forecasts, as well as the
        historical data points.

        Parameters
        ----------
        normalized :
            normalize the forecast by the baseline
        month_to_quarters :
            whether to aggregate monthly data to quarters before plotting
        start_date :
            Only include data from this date forward in the summary
        """
        # Summarize
        S = self.get_summary(
            quarterly=month_to_quarters, start_date=start_date
        ).loc["Total"]

        # Get the components
        baseline = S.loc["baseline"]
        forecast = S.loc["forecast"]
        actuals = S.loc["actual"]

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
                    clip_on=False,
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
                    clip_on=False,
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
                    clip_on=False,
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
                    clip_on=False,
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
                    clip_on=False,
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


class ScenarioForecast:
    """
    A collection of revenue forecasts for different taxes for a
    specific scenario.

    Parameters
    ----------
    *forecasts :
        individual RevenueForecast objects for each tax forecast
    scenario :
        if provided, call `run_forecast(scenario)` for each of the input forecasts.
    """

    def __init__(self, *forecasts: RevenueForecast, scenario=None):

        # Save the forecasts as a dict
        self.forecasts = {f.tax_name: f for f in forecasts}

        # Run the specified forecast
        if scenario is not None:
            for name in self.forecasts:
                self.forecasts[name].run_forecast(scenario)

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

    def _get_report(
        self,
        func_name,
        include_sectors=False,
        quarterly=False,
        start_date=None,
        **kwargs,
    ):
        """Internal function to calculate a specific report."""

        out = []
        for tax_name in self:

            # Get the tax object
            tax = self[tax_name]

            # Get the function
            func = getattr(tax, func_name)

            # Call it
            summary = func(
                include_sectors=include_sectors,
                quarterly=quarterly,
                start_date=start_date,
                **kwargs,
            )

            # Rename the index level so it includes tax
            summary = pd.concat({tax.tax_name: summary}, names=["tax"])
            summary = summary.rename_axis(("tax", "sector", "kind"))

            out.append(summary)

        # Combine
        # Date is now on column axis with taxes on row axis
        out = pd.concat(out, axis=0)

        # Add a "all taxes" column
        all_taxes = out.xs("Total", axis=0, level=1).sum(axis=0, level=-1)
        for name in all_taxes.index:
            out.loc[("all_taxes", "Total", name)] = all_taxes.loc[name]

        # Re-order
        out = out.loc[self.taxes + ["all_taxes"]]

        # Return just the total
        if not include_sectors:
            out = out.xs("Total", axis=0, level=1)

        return out

    def get_summary(
        self,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Summarize the scenario by providing actual, baseline,
        and forecast values for each tax.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by tax, sector and kind, where kind includes
            "actual", "forecast" and "baseline". Columns are dates.
        """
        return self._get_report(
            "get_summary",
            include_sectors=include_sectors,
            quarterly=quarterly,
            start_date=start_date,
        )

    def get_normalized_summary(
        self, include_sectors=False, quarterly=False, start_date=None
    ) -> pd.DataFrame:
        """
        Return the actuals & forecast normalized by the baseline.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by sector and kind, where kind includes
            "actual" and "forecast". Columns are dates.
        """
        # Get the summary
        S = self.get_summary(
            include_sectors=include_sectors,
            quarterly=quarterly,
            start_date=start_date,
        )

        # Get the baseline
        baseline = S.xs("baseline", axis=0, level=-1)

        # Create a copy to return and remove baseline
        out = S.copy().drop("baseline", level=-1)
        for name in ["forecast", "actual"]:

            # Normalize the actuals/forecast
            F = S.xs(name, axis=0, level=-1)
            F = F / baseline

            # Set it!
            if include_sectors:
                idx = pd.IndexSlice[:, :, name]
            else:
                idx = pd.IndexSlice[:, name]
            out.loc[idx, :] = F.values

        return out

    def get_baseline_differences(
        self,
        cumulative: bool = True,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return the differences between the baseline and actuals/forecast.

        Note: you must call `run_forecast()` before this.

        Parameters
        ----------
        cumulative :
            whether to return cumulative difference since the specified start date
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters
        start_date :
            Only include data from this date forward in the summary

        Returns
        -------
        summary :
            Dataframe indexed by sector and kind, where kind includes
            "actual" and "forecast". Columns are dates.
        """
        return self._get_report(
            "get_baseline_differences",
            cumulative=cumulative,
            include_sectors=include_sectors,
            quarterly=quarterly,
            start_date=start_date,
        )


@dataclass
class ScenarioComparison:
    """
    A class to facilitate comparisons of multiple scenario forecasts.

    Parameters
    ----------
    scenarios :
        dict mapping scenario name to forecast
    """

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

    def _get_report(
        self,
        func_name,
        start_date=None,
        quarterly=False,
        include_sectors=False,
        **kwargs,
    ):
        """Internal function to get scenario report."""

        out = []
        for i, scenario in enumerate(self.scenario_names):

            # This scenario
            scenario_forecast = self.scenarios[scenario]

            # Get the function
            func = getattr(scenario_forecast, func_name)

            # Run the function
            df = func(
                include_sectors=include_sectors,
                quarterly=quarterly,
                start_date=start_date,
                **kwargs,
            )

            # Rename the forecast
            df = df.rename(index={"forecast": scenario})

            # Drop baseline if we need to
            if "baseline" in df.index.get_level_values(-1):
                df = df.drop("baseline", axis=0, level=-1)

            # Drop actual if not the first
            if i > 0:
                df = df.drop("actual", axis=0, level=-1)

            out.append(df)

        # Combine
        out = pd.concat(out, axis=0).sort_index()

        # Return with "total" last
        i = out.index.get_level_values(0).unique()
        return out.loc[i.drop("all_taxes").tolist() + ["all_taxes"]]

    def get_summary(
        self,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return a summary of the scenario forecasts.

        Note: This includes actual and forecasts but not baseline.

        Parameters
        ----------
        start_date :
            Only include data from this date forward in the summary
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters

        Returns
        -------
        summary :
            Dataframe indexed by tax, sector and kind, where kind includes
            "actual" and scenario names. Columns are dates.
        """
        return self._get_report(
            "get_summary",
            start_date=start_date,
            quarterly=quarterly,
            include_sectors=include_sectors,
        )

    def get_baseline_differences(
        self,
        cumulative: bool = True,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return cumulative differences between forecast and baseline
        since the specified start date.

        Note: This includes differences between actual values and
        baseline and forecasted values and baseline.

        Parameters
        ----------
        start_date :
            Only include data from this date forward in the summary
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters

        Returns
        -------
        diffs :
            Dataframe indexed by tax, sector and kind, where kind includes
            "actual" and scenario names. Columns are dates.
        """
        return self._get_report(
            "get_baseline_differences",
            cumulative=cumulative,
            start_date=start_date,
            quarterly=quarterly,
            include_sectors=include_sectors,
        )

    def get_normalized_summary(
        self,
        include_sectors: bool = False,
        quarterly: bool = False,
        start_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return the actual and scenario forecasts normalized by
        the baseline.

        Parameters
        ----------
        start_date :
            Only include data from this date forward in the summary
        include_sectors :
            whether to include sectors
        quarterly :
            if data is monthly, whether to summarize in quarters

        Returns
        -------
        declines :
            Dataframe indexed by tax, sector and kind, where kind includes
            "actual" and scenario names. Columns are dates.
        """
        return self._get_report(
            "get_normalized_summary",
            start_date=start_date,
            quarterly=quarterly,
            include_sectors=include_sectors,
        )
