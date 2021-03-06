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
                58921540.64579399,
                66840131.486353144,
                70930906.51609391,
                64307830.926559515,
                64541043.654096015,
                73214851.42486982,
            ],
            "Non-Residential": [
                16430490.674820002,
                17094282.49808273,
                17610529.82952483,
                17964501.47909828,
                18144146.49388926,
                18325587.95882815,
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
                13605226.151016003,
                14016103.980776686,
                14297827.670790298,
                14440805.947498202,
                14585214.006973183,
                14731066.147042917,
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
