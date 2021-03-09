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
            "Total Retail",
            "Wholesale",
        ]
    }

    ASSUMPTIONS = {
        "moderate": {
            "impacted": np.repeat([0.5, 0.3, 0.2, 0.1, 0.05, 0.0, 0.0], 3),
            "default": np.repeat([0.3, 0.2, 0.1, 0.05, 0.03, 0.0, 0.0], 3),
        },
        "severe": {
            "impacted": np.repeat([0.7, 0.5, 0.3, 0.2, 0.1, 0.05, 0.0], 3),
            "default": np.repeat([0.5, 0.3, 0.2, 0.1, 0.05, 0.03, 0.0], 3),
        },
    }

    def __init__(self, fresh=False):
        super().__init__(
            tax_name="sales",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            ignore_sectors=False,
            fit_kwargs={"seasonality_mode": "multiplicative"},
            calibrate_to_budget=False,
            city_sales_only=True,
        )
