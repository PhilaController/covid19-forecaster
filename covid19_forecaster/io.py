import calendar

import pandas as pd
from phl_budget_data.clean import (
    load_birt_collections_by_sector,
    load_city_collections,
    load_rtt_collections_by_sector,
    load_sales_collections_by_sector,
    load_wage_collections_by_sector,
)

from . import DATA_DIR

MONTH_NAMES = [x.lower() for x in calendar.month_abbr]


def load_monthly_sales_tax_data():
    """Load monthly sales tax collections."""

    # Load the raw data
    sales = pd.read_excel(
        DATA_DIR / "taxes" / "monthly-sales-data.xlsx",
        sheet_name="Sales",
        usecols="B,U:AB",
        skiprows=12,
        nrows=12,
        index_col=0,
    )

    # Format it
    sales = (
        sales.melt(
            ignore_index=False, var_name="fiscal_year", value_name="total"
        )
        .rename_axis("month_name", axis=0)
        .reset_index()
        .assign(
            fiscal_year=lambda df: df.fiscal_year.str.slice(2).astype(int),
            month_name=lambda df: df.month_name.str.lower().str.slice(0, 3),
            month=lambda df: df.month_name.apply(
                lambda x: MONTH_NAMES.index(x)
            ),
            fiscal_month=lambda df: ((df.month - 7) % 12 + 1),
            year=lambda df: df.apply(
                lambda r: r["fiscal_year"]
                if r["month"] < 7
                else r["fiscal_year"] - 1,
                axis=1,
            ),
            date=lambda df: pd.to_datetime(
                df["month"].astype(str) + "/" + df["year"].astype(str)
            ),
        )
        .dropna(subset=["total"])
    )

    return sales


def load_tax_rates(tax: str) -> pd.DataFrame:
    """Load the tax rates for the specified tax."""

    # Check the allowed values
    allowed = ["birt", "npt", "parking", "rtt", "sales", "wage"]
    if tax.lower() not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

    # Load
    path = DATA_DIR / "rates" / f"{tax}.csv"
    rates = pd.read_csv(path, index_col=0)

    if tax == "wage":
        rates["rate"] = (
            0.6 * rates["rate_resident"] + 0.4 * rates["rate_nonresident"]
        )
    elif tax == "npt":
        rates["rate"] = (
            0.515 * rates["rate_resident"] + 0.485 * rates["rate_nonresident"]
        )
    elif tax == "birt":
        rates["rate"] = (
            0.75 * rates["rate_net_income"]
            + 0.25 * rates["rate_gross_receipts"]
        )

    # index is "fiscal_year" and one column "rate"
    return rates[["rate"]]


def load_data_by_sector(kind: str, use_subsectors=False) -> pd.DataFrame:
    """
    Load data for various taxes by sector.

    Parameters
    ----------
    kind : str
        load sector info for BIRT, sales tax, or wage tax
    main_sectors_only : bool, optional
        if True, only return the main sectors

    Returns
    -------
    DataFrame :
        sector info for the requested tax
    """
    allowed = ["birt", "sales", "wage", "rtt"]
    if kind not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

    LOADERS = {
        "birt": load_birt_collections_by_sector,
        "sales": load_sales_collections_by_sector,
        "wage": load_wage_collections_by_sector,
        "rtt": load_rtt_collections_by_sector,
    }

    # Load
    df = LOADERS[kind]()

    # Get the main sectors
    if not use_subsectors:
        out = df.query("parent_sector.isnull()").copy()
    # Use sub-sectors
    else:
        parent_sectors = df["parent_sector"].unique()
        out = df.query("sector not in @parent_sectors").copy()

    if kind == "birt":
        out["fiscal_year"] = out["tax_year"]
    elif kind == "rtt":
        out = out.query("sector != 'Unclassified'")

    return out


def load_monthly_collections(tax_name) -> pd.DataFrame:
    """
    Load data for monthly tax revenue collections

    Returns
    -------
    DataFrame :
        the data for collections by month
    """
    if tax_name == "sales":
        return load_monthly_sales_tax_data()

    # Load all the data
    df = load_city_collections().query("kind == 'Tax'")

    # Combine wage + earnings
    if tax_name == "wage":

        # Combine wage + earnings
        tax_names = ["wage", "earnings"]
        df = df.query("name in @tax_names")

        # Do the total
        out = df.groupby(
            [
                "fiscal_year",
                "month_name",
                "month",
                "fiscal_month",
                "year",
                "date",
            ],
            as_index=False,
        )["total"].sum()

    else:

        # Fix the tax names for some
        if tax_name == "rtt":
            tax_name = "real_estate_transfer"
        elif tax_name == "npt":
            tax_name = "net_profits"

        # Query
        out = df.query(f"name == '{tax_name}'").drop(
            labels=["kind", "name"], axis=1
        )

    if tax_name == "soda":
        out = out.query("date >= '2017-04-01'")
    elif tax_name in ["birt", "net_profits"]:

        # SOURCE: june 2020 collections report
        if tax_name == "birt":
            accrual = 261024311
        else:
            accrual = 10737282

        # Subtract from July 2020
        sel = (out["month"] == 7) & (out["year"] == 2020)
        out.loc[sel, "total"] -= accrual

        # Add to April 2020
        sel = (out["month"] == 4) & (out["year"] == 2020)
        out.loc[sel, "total"] += accrual

    return out
