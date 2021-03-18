import numpy as np
import pandas as pd

from .. import DATA_DIR
from ..core import RevenueForecast
from ..forecasters import NoBaselineForecasterBySector
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class RealtyTransferTaxForecast(NoBaselineForecasterBySector, RevenueForecast):
    """Realty transfer tax revenue forecast."""

    ASSUMPTIONS = {}

    def __init__(self, fresh=False):

        # Load the assumptions
        path = DATA_DIR / "models" / "v2" / "RTT Analysis.xlsx"
        skiprows = {"moderate": 5, "severe": 15}
        for scenario in ["moderate", "severe"]:

            # Load the data
            data = pd.read_excel(
                path,
                nrows=2,
                header=0,
                index_col=0,
                usecols="A,D:I",
                sheet_name="FY21-FY22 RTT Scenarios",
                skiprows=skiprows[scenario],
            )

            # Convert to keys --> sectors and values --> revenue
            self.ASSUMPTIONS[scenario] = {}
            for k in data.index:
                self.ASSUMPTIONS[scenario][k] = data.loc[k].tolist()

        super().__init__(
            tax_name="rtt",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            ignore_sectors=False,
            agg_after_fitting=True,
            fit_kwargs={"seasonality_mode": "additive"},
            flat_growth=True,
        )
