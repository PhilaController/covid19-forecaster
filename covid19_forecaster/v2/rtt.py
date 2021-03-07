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
                59504922.23634641,
                68170250.75816274,
                73058693.95655346,
                66892750.42746627,
                67800043.69149524,
                77673338.7114734,
            ],
            "Non-Residential": [
                16430490.674820002,
                17094282.49808273,
                17610529.82952483,
                18142367.830376476,
                18507029.423767045,
                18879020.715184763,
            ],
        },
        "severe": {
            "Residential": [
                52458286.70835801,
                59213671.75955736,
                66204647.623281255,
                59725736.97083543,
                59811270.67657426,
                67513545.93516353,
            ],
            "Non-Residential": [
                13016777.078304004,
                13542654.872267488,
                14227913.208804224,
                14947845.61716972,
                15399270.554808244,
                15864328.525563456,
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
            agg_after_fitting=True,
            fit_kwargs={"seasonality_mode": "additive"},
            flat_growth=True,
        )
