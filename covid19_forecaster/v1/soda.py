import numpy as np

from ..core import RevenueForecast
from ..forecasters import DefaultForecaster
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class SodaTaxForecast(DefaultForecaster, RevenueForecast):
    """Soda tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": np.concatenate(
            [
                np.repeat(0.2, 3),
                np.repeat(0.1, 3),
                np.repeat(0.05, 3),
                np.repeat(0.03, 3),
                np.repeat(0.01, 9),
            ]
        ),
        "severe": np.concatenate(
            [
                np.repeat(0.4, 3),
                np.repeat(0.3, 3),
                np.repeat(0.15, 3),
                np.repeat(0.05, 3),
                np.repeat(0.03, 9),
            ]
        ),
    }

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="soda",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            fit_kwargs={"seasonality_mode": "additive"},
            calibrate_to_budget=False,
        )
