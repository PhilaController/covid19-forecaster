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


class RealtyTransferTaxForecast(DefaultForecaster, RevenueForecast):
    """Realty transfer tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": np.concatenate(
            [[0, 0.25, 0.5], np.repeat(0.1, 6), np.repeat(0.05, 12)]
        ),
        "severe": np.concatenate(
            [[0, 0.25, 0.5], np.repeat(0.25, 6), np.repeat(0.1, 12)]
        ),
    }

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="rtt",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            ignore_sectors=True,
            fit_kwargs={"seasonality_mode": "multiplicative"},
        )
