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


class AmusementTaxForecast(DefaultForecaster, RevenueForecast):
    """Amusement tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": [0.9, 0.7, 0.5, 0.3, 0.1, 0.0],
        "severe": [0.9, 0.8, 0.7, 0.5, 0.3, 0.1],
    }

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="amusement",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            fit_kwargs={"seasonality_mode": "multiplicative"},
        )
