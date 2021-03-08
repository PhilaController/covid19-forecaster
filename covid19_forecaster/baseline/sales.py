"""Transform sales data by splitting between City and School District"""
import pandas as pd

from ..utils import get_fiscal_year

# School district gets $120M
MAX_DISTRICT_AMOUNT = 120e6


def get_sales_fiscal_year(r: pd.Series) -> int:
    """
    July/Aug are associated with the previous fiscal year
    due to the accrual period.
    """
    if r["month"] in [7, 8]:
        return r["fiscal_year"] - 1
    else:
        return r["fiscal_year"]


def _get_city_sales_only(df: pd.DataFrame) -> pd.DataFrame:
    """
    Internal function to extract city sales data.

    Notes
    -----
    There must be "month", "total", and "fiscal_year" columns.

    Parameters
    ----------
    df :
        sales data in tidy format

    Returns
    -------
    out :
        a copy of the input data, with
    """
    # Make sure our columns exist
    assert all(col in df.columns for col in ["month", "fiscal_year", "total"])

    # Create a copy and add the fiscal year for sales calculation
    X = df.copy()
    X["fiscal_year_sales"] = df.apply(get_sales_fiscal_year, axis=1)

    def add_sales_total(grp):
        """
        Keep track of school district portion and allocate.

        Strategy:
        - Start in September
        - Collections get split 50/50, until District hits cap
        - City gets 100% of remaining months, until new fiscal year
        """
        cnt = 0
        out = []

        months = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
        for month in months:

            # Get data for this month
            row = grp.query(f"month == {month}").copy()
            if len(row):

                # Sum up total
                total = row["total"].sum()
                school_district_fraction = 0.0

                if (
                    row.iloc[0]["fiscal_year_sales"] >= 2015
                    and cnt < MAX_DISTRICT_AMOUNT
                ):
                    school_district_fraction = 0.5
                    school_district = total * school_district_fraction
                    if cnt + school_district > 120e6:
                        school_district_fraction = (120e6 - cnt) / total

                # Add the city
                row["total"] = row["total"] * (1 - school_district_fraction)
                out.append(row)

                # Add to the cumulative count
                cnt += total * school_district_fraction

        out = pd.concat(out, axis=0, ignore_index=True)
        return out

    # Perform the calculation and return
    out = X.groupby("fiscal_year_sales").apply(add_sales_total)
    return out.drop(labels=["fiscal_year_sales"], axis=1).droplevel(
        axis=0, level=0
    )


def get_city_sales_only(X):
    """
    Return a data frame that only includes the City portion of the
    sales tax.

    School District receives 50% of monthly collections until the
    cap ($120M) is reached.

    This gives the City sales data a strong seasonality, with peaks
    in the summer months.
    """

    # Set up
    R = X.copy()
    has_sectors = X.columns.nlevels > 1

    # Add a fake column level for continuity of cases
    if not has_sectors and len(X.columns) != 1:
        R.columns = pd.MultiIndex.from_product([["total"], R.columns])
        has_sectors = True

    # Get the "total"
    R = R["total"].reset_index()

    # Using sectors
    if has_sectors:
        R = R.melt(id_vars=["date"], value_name="total", var_name="sector")

    # Put into tidy format
    R = R.assign(
        fiscal_year=lambda df: df.date.apply(get_fiscal_year),
        month=lambda df: df.date.dt.month,
    )

    # Do the allocation
    R = _get_city_sales_only(R)

    # Postprocess
    if has_sectors:

        # Pivot back
        R = R.pivot_table(index="date", values="total", columns="sector")
        R.columns = pd.MultiIndex.from_product([["total"], R.columns])

        # Add upper and lower
        if "upper" in X.columns:
            out = [R]
            for col in ["upper", "lower"]:
                tmp = X[col] / X["total"] * R["total"]
                tmp.columns = pd.MultiIndex.from_product([[col], tmp.columns])
                out.append(tmp)

            # Combine along column axis
            out = pd.concat(out, axis=1).sort_index(axis=1, level=1)
        else:
            out = R

    else:

        if "upper" in X.columns:
            out = R[["date", "total"]]
            for col in ["upper", "lower"]:
                out[col] = X[col] / X["total"] * R["total"]

            out = out.set_index("date")
        else:
            out = R.set_index("date")[["total"]]

    if has_sectors and X.columns.nlevels == 1:
        out = out["total"]

    return out
