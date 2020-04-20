from .core import ScenarioForecast


class WageTax(ScenarioForecast):
    """
    Wage tax revenue forecast.
    """

    RECOVERY_SPEED = 1.0

    RECOVERY_RATES = {
        "moderate": {"impacted": 0.15, "other": 0.25},
        "severe": {"impacted": 0.1, "other": 0.2},
    }

    IMPACTED_SECTORS = [
        "Arts, Entertainment, and Other Recreation",
        "Hotels",
        "Restaurants",
        "Retail Trade",
        "Sport Teams",
        "Wholesale Trade",
    ]

    ASSUMPTIONS = {
        "Construction": {"moderate": 0.1, "severe": 0.2},
        "Manufacturing (includes headquarter offices & factories)": {
            "moderate": 0.15,
            "severe": 0.25,
        },
        "Public Utilities": {"moderate": 0.05, "severe": 0.07},
        "Transportation and Warehousing": {"moderate": 0.15, "severe": 0.2},
        "Telecommunication": {"moderate": 0.05, "severe": 0.07},
        "Publishing, Broadcasting, and Other Information": {
            "moderate": 0.05,
            "severe": 0.07,
        },
        "Wholesale Trade": {"moderate": 0.25, "severe": 0.5},
        "Retail Trade": {"moderate": 0.15, "severe": 0.30},
        "Banking & Credit Unions": {"moderate": 0.05, "severe": 0.07},
        "Securities / Financial Investments": {
            "moderate": 0.1,
            "severe": 0.15,
        },
        "Insurance": {"moderate": 0.05, "severe": 0.07},
        "Real Estate, Rental and Leasing": {"moderate": 0.05, "severe": 0.07},
        "Health and Social Services": {"moderate": 0.07, "severe": 0.15},
        "Education": {"moderate": 0.07, "severe": 0.15},
        "Professional  Services": {"moderate": 0.05, "severe": 0.07},
        "Hotels": {"moderate": 0.25, "severe": 0.50},
        "Restaurants": {"moderate": 0.5, "severe": 0.75},
        "Sport Teams": {"moderate": 0.25, "severe": 0.50},
        "Arts, Entertainment, and Other Recreation": {
            "moderate": 0.2,
            "severe": 0.3,
        },
        "Other Sectors": {"moderate": 0.15, "severe": 0.25},
        "Government": {"moderate": 0, "severe": 0.05},
        "Unclassified Accounts": {"moderate": 0.05, "severe": 0.07},
    }

    @property
    def tax_name(self):
        return "wage"

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

        # Initial drop
        initial_drop = self.ASSUMPTIONS[sector][scenario]

        # Impacted sector?
        if sector in self.IMPACTED_SECTORS:
            recovery_rate = self.RECOVERY_RATES[scenario]["impacted"]
        else:
            recovery_rate = self.RECOVERY_RATES[scenario]["other"]

        return initial_drop * (1 - recovery_rate) ** (
            month_offset * self.RECOVERY_SPEED
        )

    def save_to_template(self):
        """
        Save the forecast to a template Excel spreadsheet.
        """
        super().save_to_template("Wage Scenario Analysis", 75)
