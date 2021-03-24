# Forecast range
FORECAST_START = "2021-01-01"
FORECAST_STOP = "2022-06-30"

# Baseline range
BASELINE_START = "2013-07-01"
BASELINE_STOP = "2020-03-31"

# Forecast frequency
FREQ = "Q"

# Scenario names
SCENARIOS = ["moderate", "severe"]


from ..core import ScenarioComparison, ScenarioForecast
from .amusement import AmusementTaxForecast
from .birt import BIRTForecast
from .npt import NPTForecast
from .parking import ParkingTaxForecast
from .rtt import RealtyTransferTaxForecast
from .sales import SalesTaxForecast
from .soda import SodaTaxForecast
from .wage import WageTaxForecast

TAXES = [
    AmusementTaxForecast,
    BIRTForecast,
    NPTForecast,
    ParkingTaxForecast,
    RealtyTransferTaxForecast,
    SalesTaxForecast,
    SodaTaxForecast,
    WageTaxForecast,
]
