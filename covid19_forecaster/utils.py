import pandas as pd


def get_fiscal_year(date: pd.Timestamp) -> int:
    """
    Calculate the fiscal year the input datetime object
    """
    if date.month <= 6:
        return date.year
    else:
        return date.year + 1


def get_quarter(date):
    """
    Return the fiscal quarter from the date
    """
    year = date.year
    month = date.month
    fiscal_year = year if month < 7 else year + 1
    if month in [1, 2, 3]:
        quarter = 3
    elif month in [4, 5, 6]:
        quarter = 4
    elif month in [7, 8, 9]:
        quarter = 1
    else:
        quarter = 2
    return f"FY{str(fiscal_year)[2:]} Q{quarter}"


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
