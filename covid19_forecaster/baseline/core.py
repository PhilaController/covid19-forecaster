import calendar

import numpy as np
import pandas as pd
from fbprophet import Prophet

from ..data import (
    load_data_by_sector,
    load_monthly_collections,
    load_tax_rates,
)
from ..utils import add_date_column, get_fiscal_year
from .fyp import BIRT_REVENUES, FY20_REVENUES, FYP_GROWTH_RATES

BASELINE_MAX = "03-31-2020"


def load_historical_collections(tax_name):
    """
    Load monthly collections data and return the formatted data
    to feed into the forecast.

    Parameters
    ----------
    tax_name : str
        the name of the tax to load
    """
    # Load the monthly collections data for all taxes
    collections = load_monthly_collections()

    # Select the tax we are loading
    if tax_name == "wage":
        collections = collections.query("name == 'wage_earnings'").copy()
    elif tax_name == "npt":
        collections = collections.query("name == 'net_profits'").copy()
    elif tax_name == "rtt":
        collections = collections.query(
            "name == 'real_estate_transfer'"
        ).copy()
    else:
        collections = collections.query(f"name == '{tax_name}'").copy()

    # Add the school district totals to sales
    if tax_name == "sales":
        valid = collections["fiscal_year"] >= 2015
        collections.loc[valid, "total"] += 120e6 / 12

    # Format the sector data
    if tax_name in ["sales", "wage", "birt"]:

        # Get the sector info (for main sectors only)
        sector_info = load_data_by_sector(tax_name, main_sectors_only=True)

        # Add fiscal year for tax year for BIRT
        if tax_name == "birt":
            sector_info["fiscal_year"] = sector_info["tax_year"]

        # Extrapolate monthly totals to monthly by sector
        collections = extrapolate_collections_by_sector(
            collections, sector_info
        )

    return add_date_column(collections)


def extrapolate_collections_by_sector(collections, by_sector):
    """
    Extrapolate from a monthly collections total for all sectors
    to a monthly breakdown by sector (using historical sector information).

    Parameters
    ----------
    collections : DataFrame
        the monthly collections data
    by_sector : DataFrame
        the data for sector information, either monthly or annually
    """

    # Determine how to group
    if "month_name" in by_sector.columns:
        groupby = ["fiscal_year", "month_name", "naics_sector"]

    else:
        groupby = ["fiscal_year", "naics_sector"]

    # sum over sectors to get the fiscal year total
    by_sector_by_FY = by_sector.groupby(groupby[:-1])["total"].sum()

    # Get the sector fraction
    normalized_by_sector = (
        by_sector.groupby(groupby)["total"].sum() / by_sector_by_FY
    )

    # Loop over each month in each fiscal year
    out = []
    collections = collections.set_index(["fiscal_year", "month_name"])
    for group in collections.index:

        # make this group into a dict
        group_dict = dict(zip(collections.index.names, group))

        # this is the monthly collections total
        total = collections.loc[group]

        # rescale sector totals by the overall total
        overlapping_index = tuple(
            [
                group_dict[k]
                for k in group_dict
                if k in normalized_by_sector.index.names
            ]
        )

        # No match — we need to use historical averages
        if overlapping_index not in normalized_by_sector.index:

            levels = []
            overlapping_index = []
            for key in normalized_by_sector.index.names:
                if (
                    key in group_dict
                    and normalized_by_sector.index.isin(
                        [group_dict[key]], level=key
                    ).sum()
                    > 0
                ):
                    levels.append(key)
                    overlapping_index.append(group_dict[key])
            levels.append("naics_sector")

            sector_shares = normalized_by_sector.mean(
                level=levels, axis="index"
            )
            if len(overlapping_index):
                sector_shares = sector_shares.loc[overlapping_index[0]]
        else:
            sector_shares = normalized_by_sector.loc[overlapping_index]

        # Rescale the monthly total by the sector shares
        rescaled_collections = (sector_shares * total["total"]).reset_index()

        # Add the other values
        for key, value in group_dict.items():
            rescaled_collections[key] = value
        for col in ["month", "fiscal_month", "year"]:
            rescaled_collections[col] = total[col]

        out.append(rescaled_collections)

    return pd.concat(out)


def project_tax_revenue(
    tax_name, historical_df, seasonality_mode="multiplicative", **kwargs
):
    """
    Project the specified tax using historical data for FY21 through
    FY25.
    """
    # Load tax rates
    try:
        rates = load_tax_rates(tax_name)
    except ValueError:
        rates = None

    # Doing a sector analysis?
    sectors = None
    if "naics_sector" in historical_df:
        sectors = sorted(historical_df["naics_sector"].unique())

    def _project_tax_revenue(df):

        # Revenue to base, if we have rates
        X = df.copy()
        if rates is not None:
            X["total"] /= rates.loc[X["fiscal_year"], "rate"].values

        # Get data by year and month
        N = X.groupby(["year", "month_name"])["total"].sum().reset_index()

        # Add the month/year as a datetime
        N = add_date_column(N)

        # Rename and sort
        N = N.rename(columns={"total": "y", "date": "ds"}).sort_values("ds")

        # TRIM TO MAX BASELINE
        N = N.query(f"ds <= '{BASELINE_MAX}'")

        # Initialize and fit the model
        m = Prophet(
            seasonality_mode=seasonality_mode,
            daily_seasonality=False,
            weekly_seasonality=False,
            **kwargs,
        )
        m.fit(N[["ds", "y"]])

        # Forecast until end of FY 2025
        periods = (
            pd.to_datetime("6/30/25").to_period("M")
            - N["ds"].max().to_period("M")
        ).n

        # Forecast
        future = m.make_future_dataframe(periods=periods, freq="M")
        forecast = m.predict(future)

        # Add fiscal year
        forecast["fiscal_year"] = forecast["ds"].apply(get_fiscal_year)

        # Base to revenue if we need to
        if rates is not None:
            rate = rates.loc[forecast["fiscal_year"].tolist(), "rate"]
            for col in ["yhat", "yhat_lower", "yhat_upper"]:
                forecast[col] *= rate.values

        # Return
        cols = ["ds", "yhat", "yhat_lower", "yhat_upper"]
        return forecast[cols].rename(
            columns=dict(zip(cols, ["date", "total", "lower", "upper"]))
        )

    # Fit each sector
    if sectors is not None:
        forecast = pd.concat(
            [
                _project_tax_revenue(
                    historical_df.query(f"naics_sector == '{sector}'")
                ).assign(naics_sector=sector)
                for sector in sectors
            ]
        )
    else:
        # Fit just the total
        forecast = _project_tax_revenue(historical_df)

    # Add additional columns
    forecast = forecast.assign(
        fiscal_year=forecast["date"].apply(get_fiscal_year),
        year=forecast["date"].dt.year,
        month=forecast["date"].dt.month,
        month_name=forecast["date"].dt.month.apply(
            lambda i: calendar.month_abbr[i].lower()
        ),
        fiscal_month=((forecast["date"].dt.month - 7) % 12 + 1),
    )

    return forecast


def get_forecasted_growth_rates(tax_name, forecast):
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
    # Load tax rates
    try:
        rates = load_tax_rates(tax_name)
    except ValueError:
        rates = None

    X = forecast.copy()
    if rates is not None:
        X["total"] /= rates.loc[X["fiscal_year"], "rate"].values

    N = X.groupby(["fiscal_year"])["total"].sum().sort_index()
    return N.diff() / N.shift()


def calibrate_forecast(tax_name, raw_forecast):
    """
    Calibrate the revenue forecast to match the projections in
    the forecasted FY21 - FY25 Five Year Plan.

    Parameters
    ----------
    tax_name : str
        the name of the tax
    raw_forecast : DataFrame
        the raw revenue forecast to calibrate
    """
    # Handle BIRT separately
    if tax_name == "birt":

        # Raw annual FY totals
        raw_revenues = raw_forecast.groupby("fiscal_year")["total"].sum()

        # rescale by the correct revenue
        correction_factors = BIRT_REVENUES / raw_revenues

    # Handle everything else
    else:

        # Rescale by growth rates (if we have them)
        if tax_name in FYP_GROWTH_RATES:

            # Get tax base growth rates
            growth_rates = get_forecasted_growth_rates(tax_name, raw_forecast)

            # Rescale based on growth
            correction_factors = (
                (1 + FYP_GROWTH_RATES[tax_name]) / (1 + growth_rates)
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
        FY20_revenue = raw_forecast.query("fiscal_year == 2020")["total"].sum()
        correction_factors.loc[2020] = FY20_REVENUES[tax_name] / FY20_revenue

        # Take cumulative product
        correction_factors = correction_factors.sort_index().cumprod()

    # Merge correctation factors
    calibrated = pd.merge(
        raw_forecast,
        correction_factors.reset_index(name="correction").rename(
            columns={"index": "fiscal_year"}
        ),
        on="fiscal_year",
        how="left",
    ).assign(
        month=lambda df: df.date.dt.month, year=lambda df: df.date.dt.year,
    )

    # Calibrate!
    for col in ["total", "lower", "upper"]:
        calibrated[col] *= calibrated["correction"].fillna(1)

    return calibrated
