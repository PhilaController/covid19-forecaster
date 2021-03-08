from ..core import RevenueForecast
from ..forecasters import DefaultForecaster
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class NPTForecast(DefaultForecaster, RevenueForecast):
    """Net profits tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": [0.4, 0.4, 0.0, -0.02, -0.02, -0.05],
        "severe": [0.6, 0.6, 0.02, 0.02, 0.02, 0.03],
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
