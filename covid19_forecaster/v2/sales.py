import numpy as np

from ..core import RevenueForecast
from ..forecasters import SectorForecaster
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class SalesTaxForecast(SectorForecaster, RevenueForecast):
    """Sales tax revenue forecast."""

    GROUPS = {
        "impacted": [
            "Hotels",
            "Restaurants, bars, concessionaires and caterers",
            "Motor Vehicle Sales Tax",
        ]
    }

    ASSUMPTIONS = {
        "moderate": {
            "impacted": [0.25, 0.25, 0.2, 0.15, 0.10, 0.05],
            "default": [0.03, 0.03, 0.03, 0.02, 0.02, 0.01],
        },
        "severe": {
            "impacted": [0.3, 0.3, 0.25, 0.25, 0.2, 0.15],
            "default": [0.05, 0.05, 0.03, 0.03, 0.03, 0.03],
        },
    }

    def __init__(
        self, fresh=False,
    ):
        super().__init__(
            tax_name="sales",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            ignore_sectors=False,
            agg_after_fitting=True,
            fit_kwargs={"seasonality_mode": "additive"},
            flat_growth=True,
        )
