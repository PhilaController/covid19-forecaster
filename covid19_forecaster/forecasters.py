import pandas as pd


def check_date_bounds(date, start_date, stop_date):
    """Check the bounds of a specific date."""

    # Check min date
    if date < pd.to_datetime(start_date):
        date_str = date.strftime("%Y-%m-%d")
        raise ValueError(
            f"Date {date_str} before min forecast date ('{start_date}')"
        )

    # Check max date
    if date > pd.to_datetime(stop_date):
        date_str = date.strftime("%Y-%m-%d")
        raise ValueError(
            f"Date {date_str} after max forecast date ('{stop_date}')"
        )


class DefaultForecaster:
    """
    Default forecaster to make a prediction based on a
    decline from a baseline forecast.
    """

    ASSUMPTIONS = None

    def get_forecast_value(self, date, baseline, scenario):
        """
        For a given scenario (and optionally sector), return the revenue
        decline from the baseline forecast for the specific date.

        Parameters
        ----------
        date : pandas.Timestamp
            the date object for the month to forecast
        """
        # Check inputs
        assert self.ASSUMPTIONS is not None
        if isinstance(self.ASSUMPTIONS, dict):
            assert scenario is not None

        # Check bounds of the date
        check_date_bounds(date, self.forecast_start, self.forecast_stop)

        # Get the scenario assumptions
        declines = self.ASSUMPTIONS[scenario]

        # Check length
        if len(self.forecast_dates) != len(declines):
            raise ValueError(
                f"Size mismatch between forecast dates (length={len(self.forecast_dates)}) "
                f"and forecast declines (length={len(declines)})"
            )

        # Get the matching index
        # Default behavior: find the PREVIOUS index value if no exact match.
        i = self.forecast_dates.get_loc(date, method="ffill")

        # Retune 1 - decline
        return baseline * (1 - declines[i])


class NoBaselineForecasterBySector:
    """
    Default forecaster to make a prediction based on a
    decline from a baseline forecast.
    """

    ASSUMPTIONS = None

    def get_forecast_value(self, date, baseline, scenario):
        """
        For a given scenario (and optionally sector), return the revenue
        decline from the baseline forecast for the specific date.

        Parameters
        ----------
        date : pandas.Timestamp
            the date object for the month to forecast
        """
        # Check inputs
        assert self.ASSUMPTIONS is not None
        if isinstance(self.ASSUMPTIONS, dict):
            assert scenario is not None

        # Check bounds of the date
        check_date_bounds(date, self.forecast_start, self.forecast_stop)

        # Get the scenario assumptions
        values = self.ASSUMPTIONS[scenario]

        # Get the matching index
        # Default behavior: find the PREVIOUS index value if no exact match.
        i = self.forecast_dates.get_loc(date, method="ffill")

        out = baseline.copy()
        for sector in out.index:

            sector_values = values[sector]
            if len(self.forecast_dates) != len(sector_values):
                raise ValueError(
                    f"Size mismatch between forecast dates (length={len(self.forecast_dates)}) "
                    f"and forecast declines (length={len(sector_values)})"
                )

            out.loc[sector] = sector_values[i]

        return out


class SectorForecaster:
    """
    Default sector-based forecaster to make a prediction
    based on a decline from a baseline forecast.
    """

    GROUPS = None
    ASSUMPTIONS = None

    def get_forecast_value(self, date, baseline, scenario):
        """
        For a given scenario (and optionally sector), return the revenue
        decline from the baseline forecast for the specific date.

        Parameters
        ----------
        date : pandas.Timestamp
            the date object for the month to forecast
        """
        # Check inputs
        assert self.ASSUMPTIONS is not None
        assert self.GROUPS is not None

        # Check bounds of the date
        check_date_bounds(date, self.forecast_start, self.forecast_stop)

        # Get the scenario assumptions
        declines = self.ASSUMPTIONS[scenario]

        # Get the matching index
        # Default behavior: find the PREVIOUS index value if no exact match.
        i = self.forecast_dates.get_loc(date, method="ffill")

        out = baseline.copy()
        for sector in out.index:

            # Get the group label for this sector
            group = "default"
            for label in self.GROUPS:
                if sector in self.GROUPS[label]:
                    group = label
                    break

            sector_declines = declines[group]
            if len(self.forecast_dates) != len(sector_declines):
                raise ValueError(
                    f"Size mismatch between forecast dates (length={len(self.forecast_dates)}) "
                    f"and forecast declines (length={len(sector_declines)})"
                )

            # Multiply by 1 - decline
            out.loc[sector] *= 1 - sector_declines[i]

        return out
