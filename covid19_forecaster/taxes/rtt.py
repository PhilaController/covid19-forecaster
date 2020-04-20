from .core import ScenarioForecast
import numpy as np


class RealtyTransferTax(ScenarioForecast):
    """
    Realty transfer tax revenue forecast.
    """

    ASSUMPTIONS = {
        "moderate": np.concatenate(
            [[0, 0.25, 0.5], np.repeat(0.1, 6), np.repeat(0.05, 12)]
        ),
        "severe": np.concatenate(
            [[0, 0.25, 0.5], np.repeat(0.25, 6), np.repeat(0.1, 12)]
        ),
    }

    @property
    def tax_name(self):
        return "rtt"

    def get_forecasted_decline(self, scenario, date, sector=None):
        """
        Return the forecasted decline.

        Parameters
        ----------
        scenario : str
            the scenario to projct
        date : pandas.Timestamp
            the date object for the month to forecast
        """
        # Verify input
        assert scenario in ["moderate", "severe"]

        # monthly offset
        month_offset = self.get_month_offset(date)

        return self.ASSUMPTIONS[scenario][month_offset]

    def save_to_template(self):
        """
        Save the forecast to a template Excel spreadsheet.
        """
        super().save_to_template("RTT Scenario Analysis", 31)
