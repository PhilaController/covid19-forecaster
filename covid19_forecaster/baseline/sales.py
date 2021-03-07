"""Transform sales data by splitting between City and School District"""
import pandas as pd

from ..utils import get_fiscal_year


def get_sales_fiscal_year(r):
    """July/Aug are associated with the previous year."""
    if r["month"] in [7, 8]:
        return r["fiscal_year"] - 1
    else:
        return r["fiscal_year"]


def _get_city_sales_only(df):
    """Internal function to extract city sales data."""

    assert all(col in df.columns for col in ["month", "fiscal_year"])

    # Create a copy and add the fiscal year for sales calculation
    X = df.copy()
    X["fiscal_year_sales"] = df.apply(get_sales_fiscal_year, axis=1)

    def add_sales_total(grp):
        """Keep track of school district portion and allocate."""

        MAX_DISTRICT_AMOUNT = 120e6
        cnt = 0
        out = []

        months = [9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
        for month in months:

            row = grp.query(f"month == {month}").copy()
            if len(row):

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
    """"""

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
