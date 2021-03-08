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


import shutil
from pathlib import Path
from typing import Union

from loguru import logger

from ..core import ScenarioComparison, ScenarioForecast
from .amusement import AmusementTaxForecast
from .birt import BIRTForecast
from .npt import NPTForecast
from .output import save_model_outputs, save_scenario_results
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


def run_scenarios(fresh=False):
    """Run the scenarios."""

    scenarios = {}

    # Run all of the scenarios
    for scenario in SCENARIOS:
        logger.info(f"Running scenario '{scenario}'")

        forecasts = []
        for cls in TAXES:

            # Initialize and log
            tax = cls(fresh=fresh)
            logger.info(f"   Running forecast for '{tax.tax_name}'")

            # Run the forecast
            tax.run_forecast(scenario)

            # Save it
            forecasts.append(tax)

        # Save a scenario forecast object
        scenarios[scenario] = ScenarioForecast(*forecasts)

    comp = ScenarioComparison(scenarios)

    return comp


def run_and_save_scenarios(
    out_dir: Union[str, Path], fresh=False, clean=False
):
    """Run the scenarios and save the results."""

    # Run
    scenarios = run_scenarios(fresh=fresh)

    # Set up output directory
    if isinstance(out_dir, str):
        out_dir = Path(out_dir)

    # Remove directory?
    if out_dir.exists() and clean:
        shutil.rmtree(out_dir)

    # Make sure it exists
    if not out_dir.exists():
        out_dir.mkdir()

    # Save the scenarios
    save_scenario_results(
        scenarios, out_dir / "covid-budget-scenarios-v2.xlsx"
    )

    # Save the model inputs
    save_model_outputs(scenarios, out_dir)
