from .core import ScenarioForecast
import numpy as np


class SalesTax(ScenarioForecast):
    """
    Sales tax revenue forecast.
    """

    IMPACTED_SECTORS = [
        "Hotels",
        "Restaurants, bars, concessionaires and caterers",
        "Total Retail",
        "Wholesale",
    ]

    ASSUMPTIONS = {
        "moderate": {
            "impacted": np.repeat([0.5, 0.3, 0.2, 0.1, 0.05, 0.0, 0.0], 3),
            "other": np.repeat([0.3, 0.2, 0.1, 0.05, 0.03, 0.0, 0.0], 3),
        },
        "severe": {
            "impacted": np.repeat([0.7, 0.5, 0.3, 0.2, 0.1, 0.05, 0.0], 3),
            "other": np.repeat([0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.0], 3),
        },
    }

    @property
    def tax_name(self):
        return "sales"

    def get_forecasted_decline(self, scenario, date, sector):
        """
        Return the forecasted decline.

        Parameters
        ----------
        scenario : str
            the scenario to projct
        date : pandas.Timestamp
            the date object for the month to forecast
        sector : str, optional
            the sector to forecast
        """
        # Verify input
        assert scenario in ["moderate", "severe"]

        # monthly offset
        month_offset = self.get_month_offset(date)

        # Impacted sector?
        if sector in self.IMPACTED_SECTORS:
            drops = self.ASSUMPTIONS[scenario]["impacted"]
        else:
            drops = self.ASSUMPTIONS[scenario]["other"]

        return drops[month_offset]

    def save_to_template(self):
        """
        Save the forecast to a template Excel spreadsheet.
        """
        super().save_to_template("Sales Scenario Analysis", 57)
