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

CROSSWALK = {
    "Leisure & Hospitality": [
        "Arts, Entertainment, and Other Recreation",
        "Hotels",
        "Restaurants",
        "Sport Teams",
    ],
    "Financial activities": [
        "Banking & Credit Unions",
        "Insurance",
        "Real Estate, Rental and Leasing",
        "Securities / Financial Investments",
    ],
    "Mining, Logging, & Construction": ["Construction"],
    "Educational & Health Services": [
        "Education",
        "Health and Social Services",
    ],
    "Government": ["Government"],
    "Manufacturing": ["Manufacturing"],
    "Other services": ["Other Sectors", "Unclassified Accounts"],
    "Professional & Business Services": ["Professional Services"],
    "Trade, Transportation, & Utilities": [
        "Public Utilities",
        "Retail Trade",
        "Transportation and Warehousing",
        "Wholesale Trade",
    ],
    "Information": [
        "Publishing, Broadcasting, and Other Information",
        "Telecommunication",
    ],
}


class WageTaxForecast(NoBaselineForecasterBySector, RevenueForecast):
    """Wage tax revenue forecast."""

    ASSUMPTIONS = {}

    def __init__(
        self, fresh=False,
    ):

        # Load the assumptions
        path = DATA_DIR / "models" / "v2" / "Wage Tax Analysis.xlsx"
        skiprows = {"moderate": 23, "severe": 41}
        for scenario in ["moderate", "severe"]:

            # Load the data
            data = pd.read_excel(
                path,
                nrows=10,
                header=0,
                index_col=0,
                usecols="A,D:I",
                sheet_name="FY21-FY22 Wage Tax Scenarios",
                skiprows=skiprows[scenario],
            )

            # Convert to keys --> sectors and values --> revenue
            self.ASSUMPTIONS[scenario] = {}
            for k in data.index:
                self.ASSUMPTIONS[scenario][k] = data.loc[k].tolist()

        super().__init__(
            tax_name="wage",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            sector_crosswalk=CROSSWALK,
            agg_after_fitting=True,
            fit_kwargs={"seasonality_mode": "multiplicative"},
            flat_growth=True,
        )

    def run_forecast(self, scenario):
        """Run the forecast, adding seasonality in the severe case."""

        # Run the base
        self.forecast_ = super().run_forecast(scenario)

        # Get the seasonality
        baseline = self.baseline_forecast.forecasted_revenue_.copy()
        seasonality = baseline["yearly"] / baseline["trend"]

        # Get ratio of trends to actuals
        trend_to_actuals = (
            baseline["trend"] / self.baseline_forecast.actual_revenue_
        )

        # Calibrate to 4th of calendar year
        TA = trend_to_actuals.loc[:"2020-01"].copy()
        TA.index = TA.index.quarter
        TREND_FACTOR = TA.loc[4].mean()

        # Apply seasonality
        start = self.forecast_start
        self.forecast_.loc[start:] *= (
            1 + seasonality.loc[start:]
        ) * TREND_FACTOR

        return self.forecast_
