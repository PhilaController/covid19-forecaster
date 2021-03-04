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
        "moderate": [0.05, 0.05, 0.05, 0.0, 0, 0.025],
        "severe": [0.1, 0.1, 0.1, 0.05, 0.05, 0.0],
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
        )
