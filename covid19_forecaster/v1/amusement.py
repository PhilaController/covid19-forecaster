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
        "moderate": np.concatenate(
            [
                np.repeat(0.7, 3),
                np.repeat(0.4, 3),
                np.repeat(0.25, 3),
                np.repeat(0.15, 12),
            ]
        ),
        "severe": np.concatenate(
            [
                np.repeat(0.9, 3),
                np.repeat(0.6, 3),
                np.repeat(0.3, 3),
                np.repeat(0.2, 3),
                np.repeat(0.15, 9),
            ]
        ),
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
