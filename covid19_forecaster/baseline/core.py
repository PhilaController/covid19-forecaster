from collections import OrderedDict
from dataclasses import dataclass, field
from functools import partial
from typing import Dict, List, Optional

import pandas as pd
from cached_property import cached_property
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer

from .. import DATA_DIR, io
from ..utils import aggregate_to_quarters, get_unique_id
from .transformers import (
    BaselineForecaster,
    DisaggregateCollectionsBySector,
    RevenueToTaxBase,
)


def _has_sectors(tax_name: str, ignore_sectors: bool) -> bool:
    """Determine whether we are doing a sector-based forecast."""
    return tax_name in ["birt", "sales", "wage", "rtt"] and not ignore_sectors


def _crosswalk_sectors(
    df: pd.DataFrame, crosswalk: Dict[str, List[str]]
) -> pd.DataFrame:
    """Internal function to perform a crosswalk across sectors."""

    # Loop over keys of crosswalk -> these are the new groupings
    # Columns are the old groupings
    out = []
    for name in crosswalk:
        X = df[crosswalk[name]].sum(axis=1).rename(name)
        out.append(X)

    return pd.concat(out, axis=1)


def _get_monthly_total(df):
    """Internal utility to get the monthly total."""
    return df.groupby("date")["total"].sum().sort_index()


class cached_baseline:
    """Convenience wrapper to check if cached baseline is present."""

    def __init__(self, func):
        self.function = func

    def __get__(self, instance, owner):
        return partial(self.__call__, instance)

    def __call__(self, baseline, X):
        """Decorator that checks cache first, and then calls function."""

        # Get the cache path
        path = self.get_cache_path(baseline)

        # Call if we need to
        if baseline.fresh or not path.exists():

            # Call the function
            out = self.function(baseline, X)

            # Setup output path
            path = self.get_cache_path(baseline)
            if not path.parent.exists():
                path.parent.mkdir()

            # Save
            out.to_csv(path)
        else:
            # Load from disk
            out = self.load_from_cache(baseline)

        return out

    def get_cache_identifier(self, baseline):
        """Cache path for baseline data."""

        # Get the params that go into the hash
        d = {}
        for key in [
            "use_subsectors",
            "ignore_sectors",
            "freq",
            "fit_start_date",
            "fit_stop_date",
        ]:
            d[key] = getattr(baseline, key)

        # Add fit kwargs
        d.update(baseline.fit_kwargs)

        # Get the hash string
        return get_unique_id(d)

    def get_cache_path(self, baseline):
        """Return the cache path."""

        # Get the file path
        tag = self.get_cache_identifier(baseline)
        return DATA_DIR / "cache" / f"{baseline.tax_name}-baseline-{tag}.csv"

    def load_from_cache(self, baseline):
        """Load a cached baseline."""

        # Get the file path
        path = self.get_cache_path(baseline)
        assert path.exists()

        # Number of headers in cached CSV
        if _has_sectors(baseline.tax_name, baseline.ignore_sectors):
            header = [0, 1]
        else:
            header = [0]

        # Return
        return pd.read_csv(path, index_col=0, parse_dates=[0], header=header)


@dataclass
class BaselineForecast:
    """
    A baseline tax revenue forecast, produced using Facebook's
    Prophet tool on using collections data.

    Parameters
    ----------
    tax_name :
        the name of the tax to fit
    freq :
        the prediction frequency, either 'M' (monthly) or 'Q' (quarterly)
    fit_start_date :
        where to begin fitting the baseline
    fit_stop_date :
        where to stop fitting the baseline
    forecast_stop_date :
        where to stop the baseline forecast
    ignore_sectors :
        do not disaggregate actual data into sectors (if possible)
    use_subsectors :
        whether to disaggregate with parent sectors or subsectors
    fresh :
        whether to use the cached baseline, or generate a fresh copy
    fit_kwargs :
        any additional fitting keywords to pass to Prophet
    sector_crosswalk :
        a cross walk from old to new sector definitions
    """

    tax_name: str
    freq: str
    fit_start_date: str = "2014-07-01"
    fit_stop_date: str = "2020-03-31"
    ignore_sectors: Optional[bool] = False
    use_subsectors: Optional[bool] = False
    fresh: Optional[bool] = False
    fit_kwargs: Optional[dict] = field(default_factory=dict)
    sector_crosswalk: Optional[Dict[str, List[str]]] = None

    def __post_init__(self):

        # Check parameter values
        assert self.freq in ["M", "Q"]
        assert self.tax_name in [
            "wage",
            "birt",
            "amusement",
            "npt",
            "parking",
            "rtt",
            "sales",
            "soda",
        ]

        # Load the actual data
        self.actuals_raw = io.load_monthly_collections(self.tax_name)

        # Construct the pipeline
        self.steps = OrderedDict()

        # ------------------------------------------------------------
        # STEP 1: Disaggregate monthly totals by sector and reshape
        # ------------------------------------------------------------
        if _has_sectors(self.tax_name, self.ignore_sectors):
            self.steps["disaggregate_by_sector"] = FunctionTransformer(
                self.disaggregate_by_sector
            )
        else:
            self.steps["reshape_raw_actuals"] = FunctionTransformer(
                self.reshape_raw_actuals
            )

        # -----------------------------------------------------------------
        # STEP 2: Aggregate to quarters (optional)
        # -----------------------------------------------------------------
        if self.freq == "Q":
            self.steps["aggregate_to_quarters"] = FunctionTransformer(
                aggregate_to_quarters
            )

        # -----------------------------------------------------------------
        # STEP 3: Convert revenue to tax base
        # -----------------------------------------------------------------
        self.steps["to_tax_base"] = FunctionTransformer(self.to_tax_base)

        # -----------------------------------------------------------------
        # STEP 4: Generate the tax base baseline forecast from the actuals
        # -----------------------------------------------------------------
        self.steps["fit_tax_base"] = FunctionTransformer(self.fit_tax_base)

        # -----------------------------------------------------------------
        # STEP 5: Convert back to revenue
        # -----------------------------------------------------------------
        self.steps["to_revenue"] = FunctionTransformer(self.to_revenue)

        # -----------------------------------------------------------------
        # FINAL: Create the pipeline that runs all of the above steps
        # -----------------------------------------------------------------
        self.pipeline = Pipeline(self.steps.items())

    @cached_property
    def forecasted_revenue_(self):
        """The predicted revenue forecast."""
        return self.pipeline.fit_transform(self.actuals_raw)

    @cached_property
    def forecasted_tax_base_(self):
        """The predicted tax base forecast."""
        return self.to_tax_base(self.forecasted_revenue_)

    @cached_property
    def forecasted_total_revenue_(self):
        """The predicted total revenue forecast, summed over any sectors"""
        return self.sum_over_sectors(self.forecasted_revenue_["total"])

    @cached_property
    def forecasted_total_tax_base_(self):
        """The predicted total tax base forecast, summed over any sectors"""
        return self.sum_over_sectors(self.forecasted_tax_base_["total"])

    @cached_property
    def actual_revenue_(self):
        """The actual, processed revenue data"""

        # Steps we will skip
        skip = ["to_tax_base", "fit_tax_base", "to_revenue"]

        # Start from raw actuals and then transform
        X = self.actuals_raw
        for (name, step) in self.pipeline.steps:
            if name not in skip:
                X = step.fit_transform(X)

        return X

    @cached_property
    def actual_tax_base_(self):
        """The actual, processed revenue data"""
        return self.to_tax_base(self.actual_revenue_)

    @cached_property
    def actual_total_revenue_(self):
        """The actual revenue data, summed over any sectors"""
        return self.sum_over_sectors(self.actual_revenue_)

    @cached_property
    def actual_total_tax_base_(self):
        """The actual tax base data, summed over any sectors"""
        return self.sum_over_sectors(self.actual_tax_base_)

    def disaggregate_by_sector(self, X):
        """STEP: Disaggregate input actuals by sector."""

        # Load the sector
        sector_data = io.load_data_by_sector(
            self.tax_name, use_subsectors=self.use_subsectors
        )

        # Disaggregate actuals by sector
        sector_transformer = DisaggregateCollectionsBySector(sector_data)
        X = sector_transformer.fit_transform(X)

        # Pivot so each sector has its own column
        X = X.pivot_table(index="date", values="total", columns="sector")

        # Now do any cross walk if we need to
        if self.sector_crosswalk is not None:
            X = _crosswalk_sectors(X, self.sector_crosswalk)

        return X

    def reshape_raw_actuals(self, X):
        """STEP: Reshape the input actuals so index is date and there is one column"""

        # Index is date and one column "total"
        return X.pivot_table(index="date", values="total")

    def to_tax_base(self, X):
        """STEP: Convert revenue to tax base by dividing by tax rate."""

        # Initialize the transformer and return transformed
        tax_base_transformer = RevenueToTaxBase(self.tax_name)
        return tax_base_transformer.fit_transform(X)

    @cached_baseline
    def fit_tax_base(self, X):
        """STEP: Run Prophet to fit the tax base data."""

        # Initialize the baseline
        baseline = BaselineForecaster(
            fit_start_date=self.fit_start_date,
            fit_stop_date=self.fit_stop_date,
            fit_kwargs=self.fit_kwargs,
            forecast_stop_date="2025-06-30",
        )

        # Transform
        return baseline.fit_transform(X)

    def to_revenue(self, X):
        """STEP: Convert tax base to revenue by multiplying by tax rate."""

        # Initialize the transformer and return transformed
        tax_base_transformer = RevenueToTaxBase(self.tax_name)
        return tax_base_transformer.inverse_transform(X)

    def sum_over_sectors(self, X):
        """Convenience function to (optionally) sum over sectors."""
        if self.has_sectors:
            return X.sum(axis=1)
        else:
            return X.squeeze()

    @property
    def sectors(self):
        """The names of the sectors fit if the data is sector-based."""
        if self.has_sectors:
            return self.forecasted_revenue_.columns.get_level_values(
                level=-1
            ).unique()
        else:
            return []

    @property
    def inferred_freq(self):
        """The frequency inferred from the data used in the fit."""
        return self.actual_revenue_.index.inferred_freq

    @property
    def has_sectors(self):
        """Whether a baseline was fit for multiple sectors."""
        return self.forecasted_revenue_.columns.nlevels > 1

    @property
    def mean_abs_error(self):
        """The mean absolute error of the fit."""

        P = self.forecasted_total_revenue_
        H = self.actual_total_revenue_
        diff = (H - P).loc[self.fit_start_date : self.fit_stop_date]

        return diff.dropna().abs().mean()

    @property
    def mean_abs_percent_error(self):
        """Mean absolute percent error of the fit."""

        P = self.forecasted_total_revenue_
        H = self.actual_total_revenue_
        diff = ((H - P) / H).loc[self.fit_start_date : self.fit_stop_date]

        return diff.dropna().abs().mean()

    @property
    def mean_rms(self):
        """The average root mean squared error of the fit."""

        P = self.forecasted_total_revenue_
        H = self.actual_total_revenue_
        diff = ((H - P) ** 2).loc[self.fit_start_date : self.fit_stop_date]

        return diff.dropna().mean() ** 0.5

    def plot(self, sector=None):
        """Plot the total forecast, as well as the historical data points."""

        from matplotlib import pyplot as plt
        from phila_style import get_digital_standards
        from phila_style.matplotlib import get_theme

        # Load the palettes
        palette = get_digital_standards()

        if sector is not None:
            assert sector in self.sectors

        with plt.style.context(get_theme()):

            fig, ax = plt.subplots(
                figsize=(6, 4), gridspec_kw=dict(left=0.15, bottom=0.1)
            )

            def _transform(X, sector):
                if self.has_sectors:
                    if sector is not None:
                        X = X[sector]
                    else:
                        X = X.sum(axis=1)
                return X

            # Plot the prediction
            total = _transform(self.forecasted_revenue_["total"], sector)
            total.plot(
                lw=1,
                ax=ax,
                color=palette["dark-ben-franklin"],
                zorder=10,
                legend=False,
            )

            # Uncertainty
            lower = _transform(self.forecasted_revenue_["lower"], sector)
            upper = _transform(self.forecasted_revenue_["upper"], sector)
            ax.fill_between(
                lower.index,
                lower.values,
                upper.values,
                facecolor=palette["dark-ben-franklin"],
                alpha=0.7,
                zorder=9,
            )

            # Plot the historical scatter
            H = _transform(self.actual_revenue_, sector)
            ax.scatter(
                H.index, H.values, color=palette["love-park-red"], zorder=11,
            )

            # Format
            ax.set_yticks(ax.get_yticks())
            ax.set_yticklabels([f"${x/1e6:.0f}M" for x in ax.get_yticks()])
            ax.set_xlabel("")
            ax.set_ylabel("")

            return fig, ax
