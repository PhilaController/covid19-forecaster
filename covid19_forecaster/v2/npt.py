from ..core import RevenueForecast
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class NPTForecast(RevenueForecast):
    """Net profits tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": {2020: 0.1, 2021: 0.15, 2022: 0.05},
        "severe": {2020: 0.1, 2021: 0.2, 2022: 0.1},
    }

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="npt",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            fit_kwargs={"seasonality_mode": "additive"},
        )

    def get_forecasted_decline(self, date, baseline, scenario):
        """Return the forecasted decline."""

        assert scenario in ["moderate", "severe"]

        decline = self.ASSUMPTIONS[scenario][date.year]
        return baseline * (1 - decline)
