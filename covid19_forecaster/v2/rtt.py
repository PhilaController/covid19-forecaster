import numpy as np

from ..core import RevenueForecast
from ..forecasters import NoBaselineForecasterBySector
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)


class RealtyTransferTaxForecast(NoBaselineForecasterBySector, RevenueForecast):
    """Realty transfer tax revenue forecast."""

    ASSUMPTIONS = {
        "moderate": {
            "Residential": [
                60521096.17200125,
                69334403.7291112,
                78434456.8692276,
                71814814.42013204,
                72788867.61669672,
                83388653.76757099,
            ],
            "Non-Residential": [
                7921844.4,
                22403305.840000004,
                21861733.950000003,
                20090005.109999996,
                20491805.212199997,
                20901641.316443995,
            ],
        },
        "severe": {
            "Residential": [
                56038052.01111226,
                62939727.42294043,
                70020512.05825898,
                62853904.25335132,
                59334408.01176593,
                66642064.33017224,
            ],
            "Non-Residential": [
                6469506.26,
                18532146.375,
                18289555.200000003,
                15978015.760000002,
                15978015.760000002,
                15978015.760000002,
            ],
        },
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
            ignore_sectors=False,
            fit_kwargs={"seasonality_mode": "multiplicative"},
        )
