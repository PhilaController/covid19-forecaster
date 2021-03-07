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


class ParkingTaxForecast(DefaultForecaster, RevenueForecast):
    """Parking tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": [0.5, 0.4, 0.3, 0.2, 0.1, 0.1],
        "severe": [0.5, 0.5, 0.4, 0.3, 0.3, 0.2],
    }

    def __init__(self, fresh=False):

        # Initialize the underlying forecast class
        super().__init__(
            tax_name="parking",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            agg_after_fitting=False,
            fit_kwargs={"seasonality_mode": "multiplicative"},
            flat_growth=True,
        )
