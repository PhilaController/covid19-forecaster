from . import DATA_DIR
import pandas as pd

__all__ = ["load_monthly_collections", "load_data_by_sector"]


def load_data_by_sector(kind) -> pd.DataFrame:
    """
    Load data for various taxes by sector.

    Parameters
    ----------
    kind : str
        load sector info for BIRT, sales tax, or wage tax
    
    Returns
    -------
    DataFrame :
        sector info for the requested tax
    """
    allowed = ["birt", "sales", "wage"]
    if kind.lower() not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

    path = DATA_DIR / "revenue-reports" / f"{kind.lower()}_by_sector.csv"
    return pd.read_csv(path)


def load_monthly_collections(kind: str) -> pd.DataFrame:
    """
    Load data for monthly collections

    Parameter
    ----------
    kind : str
        load collections for tax, non-tax, or other govts
    
    Returns
    -------
    DataFrame :
        the data for collections by month
    """
    allowed = ["Tax", "Non-Tax", "Other Govts"]
    if kind not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

    tag = "_".join([w.lower() for w in kind.replace("-", " ").split()])
    path = DATA_DIR / "revenue-reports" / f"monthly-collections_{tag}.csv"

    return pd.read_csv(path)
