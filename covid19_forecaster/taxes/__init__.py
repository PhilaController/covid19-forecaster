from .sales import SalesTax
from .rtt import RealtyTransferTax
from .amusement import AmusementTax
from .parking import ParkingTax
from .soda import SodaTax
from .wage import WageTax
from .birt import BIRT
from .npt import NPT
from .. import DATA_DIR

TAXES = [
    WageTax,
    SalesTax,
    RealtyTransferTax,
    BIRT,
    SodaTax,
    ParkingTax,
    AmusementTax,
    NPT,
]


def run_forecasts(filename, fresh=False):
    """
    Run forecasts and update the assumptions.

    Parameters
    ----------
    filename : str
        the name of the file to save
    fresh : bool, optional
        run fresh baseline forecasts?
    """
    import shutil

    # Save the new forecasts
    for tax in TAXES:
        tax(fresh=fresh).save_to_template()

    # Save the assumptions page too
    save_quarterly_declines()

    # Make the copy
    template_file = (
        DATA_DIR / "templates" / "Budget Impact Analysis Template.xlsx"
    )
    shutil.copy(template_file, filename)


def save_quarterly_declines():
    """
    Save the quarterly declines to the template file.
    """

    import openpyxl
    import pandas as pd

    sheet_name = "Assumptions"
    filename = DATA_DIR / "templates" / "Budget Impact Analysis Template.xlsx"
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:

        # Copy over the sheets
        book = openpyxl.load_workbook(filename)
        writer.book = book
        writer.sheets = dict((ws.title, ws) for ws in book.worksheets)

        taxes = [t() for t in TAXES]
        startrow = 5
        for tax in taxes:
            declines = tax.get_assumptions_matrix(by_quarter=True)

            for i, scenario in enumerate(tax.SCENARIOS):
                startcol = 0 if i == 0 else 10

                data = declines.loc[scenario]
                if isinstance(data, pd.Series):
                    data = data.to_frame(name="Total").T
                data.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    startrow=startrow,
                    startcol=startcol,
                    merge_cells=False,
                    header=None,
                )

            startrow += len(data)
            startrow += 5
