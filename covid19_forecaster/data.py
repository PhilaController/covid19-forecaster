from . import DATA_DIR
import pandas as pd

__all__ = ["load_tax_rates", "load_monthly_collections", "load_data_by_sector"]


SECTORS = {
    "birt": [
        "Construction",
        "Manufacturing, subtotal",
        "Wholesale Trade",
        "Retail Trade",
        "Transportation and Storage",
        "Information, subtotal",
        "Banking and Related Activities",
        "Financial Investment Services",
        "Insurance",
        "Real Estate (including REITS)",
        "Professional Services, subtotal",
        "Business Support Services **1",
        "Educational Services",
        "Health and Social Services",
        "Sports",
        "Hotels and Other Accommodations",
        "Restaurants, Bars, and Other Food Services",
        "Other Services  **2",
        "All Other Sectors",
        "Unclassified",
    ],
    "sales": [
        "Construction",
        "Manufacturing",
        "Public Utilities",
        "Telecommunications",
        "Wholesale",
        "Car and truck rental",
        "Rentals except car and truck rentals",
        "Repair services",
        "Services other than repair services",
        "Hotels",
        "Restaurants, bars, concessionaires and caterers",
        "All Other Sectors",
        "Total Retail",
    ],
    "wage": [
        "Construction",
        "Manufacturing (includes headquarter offices & factories)",
        "Public Utilities",
        "Transportation and Warehousing",
        "Telecommunication",
        "Publishing, Broadcasting, and Other Information",
        "Wholesale Trade",
        "Retail Trade",
        "Banking & Credit Unions",
        "Securities / Financial Investments",
        "Insurance",
        "Real Estate, Rental and Leasing",
        "Health and Social Services",
        "Education",
        "Professional  Services",
        "Hotels",
        "Restaurants",
        "Sport Teams",
        "Arts, Entertainment, and Other Recreation",
        "Other Sectors",
        "Government",
        "Unclassified Accounts",
    ],
}


def load_tax_rates(tax: str) -> pd.DataFrame:
    """
    Load the tax rates for the specified tax.
    """
    allowed = ["birt", "npt", "parking", "rtt", "sales", "wage"]
    if tax.lower() not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

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

    return rates


def load_data_by_sector(kind: str, main_sectors_only=False) -> pd.DataFrame:
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
    allowed = ["birt", "sales", "wage"]
    if kind not in allowed:
        raise ValueError(f"Allowed values are: {allowed}")

    # Load the data
    path = DATA_DIR / "revenue-reports" / f"{kind}_by_sector.csv"
    out = pd.read_csv(path)

    if main_sectors_only:
        out = out.query(f"naics_sector in {SECTORS[kind]}")

    return out


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

    # Load
    tag = "_".join([w.lower() for w in kind.replace("-", " ").split()])
    path = DATA_DIR / "revenue-reports" / f"monthly-collections_{tag}.csv"
    out = pd.read_csv(path)

    # Combine Wage + Earnings
    if kind == "Tax":
        out = pd.concat(
            [
                out,
                out.query("name in ['wage', 'earnings']")
                .groupby(
                    [
                        "month",
                        "year",
                        "fiscal_year",
                        "month_name",
                        "fiscal_month",
                    ]
                )["total"]
                .sum()
                .reset_index()
                .assign(name="wage_earnings"),
            ],
            axis=0,
        ).sort_values(["fiscal_year", "fiscal_month"])

    return out
