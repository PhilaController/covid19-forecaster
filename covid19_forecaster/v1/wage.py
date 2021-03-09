import numpy as np

from ..core import RevenueForecast
from ..forecasters import check_date_bounds
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class WageTaxForecast(RevenueForecast):
    """Wage tax revenue forecast."""

    RECOVERY_RATES = {
        "moderate": {"impacted": 0.15, "default": 0.25},
        "severe": {"impacted": 0.1, "default": 0.2},
    }

    GROUPS = {
        "impacted": [
            "Arts, Entertainment, and Other Recreation",
            "Hotels",
            "Restaurants",
            "Retail Trade",
            "Sport Teams",
            "Wholesale Trade",
        ]
    }

    ASSUMPTIONS = {
        "moderate": {
            "Construction": 0.1,
            "Manufacturing": 0.15,
            "Public Utilities": 0.05,
            "Transportation and Warehousing": 0.15,
            "Telecommunication": 0.05,
            "Publishing, Broadcasting, and Other Information": 0.05,
            "Wholesale Trade": 0.25,
            "Retail Trade": 0.25,
            "Banking & Credit Unions": 0.05,
            "Securities / Financial Investments": 0.1,
            "Insurance": 0.05,
            "Real Estate, Rental and Leasing": 0.05,
            "Health and Social Services": 0.1,
            "Education": 0.1,
            "Professional Services": 0.05,
            "Hotels": 0.25,
            "Restaurants": 0.7,
            "Sport Teams": 0.25,
            "Arts, Entertainment, and Other Recreation": 0.25,
            "Other Sectors": 0.15,
            "Government": 0.03,
            "Unclassified Accounts": 0.05,
        },
        "severe": {
            "Construction": 0.2,
            "Manufacturing": 0.3,
            "Public Utilities": 0.1,
            "Transportation and Warehousing": 0.3,
            "Telecommunication": 0.1,
            "Publishing, Broadcasting, and Other Information": 0.1,
            "Wholesale Trade": 0.5,
            "Retail Trade": 0.5,
            "Banking & Credit Unions": 0.1,
            "Securities / Financial Investments": 0.2,
            "Insurance": 0.1,
            "Real Estate, Rental and Leasing": 0.1,
            "Health and Social Services": 0.2,
            "Education": 0.2,
            "Professional Services": 0.1,
            "Hotels": 0.5,
            "Restaurants": 0.9,
            "Sport Teams": 0.5,
            "Arts, Entertainment, and Other Recreation": 0.5,
            "Other Sectors": 0.3,
            "Government": 0.05,
            "Unclassified Accounts": 0.1,
        },
    }

    def get_forecasted_decline(self, date, baseline, scenario):
        """
        For a given scenario (and optionally sector), return the revenue
        decline from the baseline forecast for the specific date.

        Parameters
        ----------
        date : pandas.Timestamp
            the date object for the month to forecast
        """
        # Check bounds of the date
        check_date_bounds(date, self.forecast_start, self.forecast_stop)

        # Get the scenario assumptions
        initial_declines = self.ASSUMPTIONS[scenario]

        # Get the matching index
        # Default behavior: find the PREVIOUS index value if no exact match.
        i = self.forecast_dates.get_loc(date, method="ffill")

        out = baseline.copy()
        for sector in out.index:

            # Make sure we have this sector
            assert sector in initial_declines, sector

            # Get the group label for this sector
            group = "default"
            for label in self.GROUPS:
                if sector in self.GROUPS[label]:
                    group = label
                    break

            # The recovery rate
            recovery_rate = self.RECOVERY_RATES[scenario][group]

            # The initial drop
            initial_drop = initial_declines[sector]

            # Get the decline
            if scenario == "moderate" and i in [0, 1]:
                decline = initial_drop
            elif scenario == "severe" and i in [0, 1, 2]:
                decline = initial_drop
            else:
                decline = initial_drop * (1 - recovery_rate) ** i

            # Multiply by 1 - decline
            out.loc[sector] *= 1 - decline

        return out

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="wage",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            fit_kwargs={"seasonality_mode": "multiplicative"},
        )
