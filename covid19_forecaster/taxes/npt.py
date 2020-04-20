from .core import ShiftedScenarioForecast


class NPT(ShiftedScenarioForecast):
    """
    Net Profits tax revenue forecast.
    """

    ASSUMPTIONS = {
        "moderate": {2020: 0.05, 2021: 0.1},
        "severe": {2020: 0.1, 2021: 0.15},
    }

    @property
    def tax_name(self):
        return "npt"

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

        return self.ASSUMPTIONS[scenario][date.year]

    def save_to_template(self):
        """
        Save the forecast to a template Excel spreadsheet.
        """
        super().save_to_template("NPT Scenario Analysis", 31)
