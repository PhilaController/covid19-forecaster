from ..core import RevenueForecast
from ..utils import get_fiscal_year
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
        "moderate": {2020: 0.1, 2021: 0.3, 2022: 0.02},
        "severe": {2020: 0.1, 2021: 0.4, 2022: 0.05},
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
            agg_after_fitting=False,
            fit_kwargs={"seasonality_mode": "additive"},
            flat_growth=True,
        )

    def get_forecasted_decline(self, date, baseline, scenario):
        """Return the forecasted decline."""

        assert scenario in ["moderate", "severe"]

        fiscal_year = get_fiscal_year(date)
        decline = self.ASSUMPTIONS[scenario][fiscal_year]
        return baseline * (1 - decline)
