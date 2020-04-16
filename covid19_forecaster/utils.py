import pandas as pd


def get_fiscal_year(date: pd.Timestamp) -> int:
    """
    Calculate the fiscal year the input datetime object
    """
    if date.month <= 6:
        return date.year
    else:
        return date.year + 1


def add_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add a date column to represent the month/year.
    """
    return df.assign(
        date=pd.to_datetime(
            df.apply(lambda r: f"{r['month_name']} {r['year']}", axis=1)
        )
        + pd.offsets.MonthEnd(0)
    )
